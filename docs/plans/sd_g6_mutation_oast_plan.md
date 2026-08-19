# SD-G6 PLAN — MUTATION ENGINE + OAST ÇEKİRDEĞİ + RATE-LIMIT ENFORCEMENT

> Saldırı Dönemi Gate 6. Eski altyapı dönemi GATE 06 (Experiment Planning) ile karıştırılmaz.

## 1. ÖZET

SD-G6 avcının dişlerini takar:

- **P0 — G5 Sertleştirmesi**: `_enqueue_v3` içine IN_SCOPE kod kilidi.
- **P1 — Mutation Engine**: Gözlemlenen HTTP yüzeyinden deterministik saldırı varyantları üreten saf research katmanı.
- **P2 — OAST Çekirdeği**: Loopback callback token üretimi + callback sorgulama portu.
- **P3 — Rate-Limit Enforcement**: `program_policy.rate_limit_profile` alanının Core authorize öncesi zorlanması.

Hiçbir varyant scope dışına üretilmez; OAST token'ları provenance taşır; canlı internet çağrısı testte yasaktır.

## 2. KUTSALLAR (İHLAL = GATE AÇIK KALIR)

- **K1** Varyant scope'a hapseder: hedef node'un `scope_classification`'ından koparılamaz.
- **K2** OAST token'ları `research_run_id + hypothesis_id + target_reference` bağlı; anonim token yasak.
- **K3** Rate-limit profili zorlanır; limit aşımı DENY + ReasonCode + ledger kaydı üretir.
- **K4** G5 mühür notu: `_enqueue_v3` OUT_OF_SCOPE/UNKNOWN node ile hata verir.
- **K5** Mevcut test fonksiyonu silinmez; kontrat kopyaları md5-identical kalır.
- **K6** Ham secret OAST payload veya varyant gövdelerine girmez.

## 3. MEVCUT ZEMİN

- `GATE_05_STATUS = "PASS"`; `GATE_06` henüz tanımlı değil.
- `pytest tests/unit tests/contract -q`: **1038 passed, 4 skipped**.
- `hunt_validation.py:_enqueue_v3` IN_SCOPE kontrolü içermiyor.
- `tools/registry.py`: `SUPPORTED_REQUIREMENTS = {"loopback", "scope_derived"}`.
- `tools/http_transaction_policy.py` + `http_transaction_authorization.py`: HTTP varyant argüman validasyonu hazır.
- `execute_planned_experiment.py:authorize()` Core decision öncesi ek kontrol noktası.
- `program_policy` tablosu `daily_llm_budget_microdollars` taşıyor; `rate_limit_profile` ayrı tablo.
- `ProgramPolicyView` şu an `rate_limit_profile` taşımıyor.
- `RateLimitProfileRepository` protokolü + Postgres implementasyonu mevcut.
- `ExperimentIntent → compile_experiment_intent → ExperimentPlan` yolu hazır.
- `BudgetConsumptionRecord` + `RecordBudgetConsumption` append-only ledger hazır.

## 4. DOSYA-BAZLI DEĞİŞİKLİK PLANI

### P0 — G5 Sertleştirmesi

**Dosya**: `src/research_os/application/hunt_validation.py`
- **Fonksiyon**: `_enqueue_v3`
- **Değişiklik**: İlk satırda `node.scope_classification != ScopeClassification.IN_SCOPE` ise `HuntValidationTierError` yükselt.
- **Test**: `tests/unit/application/test_hunt_cycle.py` — yeni test: UNKNOWN node ve OUT_OF_SCOPE node ile V3 kuyruk denemesi → açık hata.

### P1 — Mutation Engine

**Dosya**: `src/research_os/research/mutation/__init__.py`
- Modül init; dışa aktarılan tipler.

**Dosya**: `src/research_os/research/mutation/types.py`
- **Sınıf**: `MutationVariant`
  - Alanlar: `variant_id`, `node_id`, `family_id`, `mutation_rule_id`, `target_reference`, `scope_classification`, `capability_id`, `action`, `arguments`, `provenance`.
- **Sınıf**: `MutationRule`
  - Alanlar: `rule_id`, `family`, `input_kind`, `output_transform`, `deterministic`.
- **Protokol**: `MutationFamily`
  - `generate(observed, node, provenance) -> tuple[MutationVariant, ...]`

**Dosya**: `src/research_os/research/mutation/families.py`
- Aile implementasyonları:
  - `ParamPollutionFamily`
  - `TypeJugglingFamily`
  - `BoundaryValueFamily`
  - `AuthHeaderVariationFamily`
  - `MethodOverrideFamily`
  - `ContentTypeConfusionFamily`
  - `IdOrTraversalCandidateFamily`
- Her aile: girdi gözlemden (EXACT_PATH/HTTP_OPERATION + parametre adayları) → deterministik varyant kümesi.
- Her varyant `provenance = {"node_id", "family_id", "mutation_rule_id"}` taşır.

**Dosya**: `src/research_os/research/mutation/engine.py`
- **Fonksiyon**: `mutate_for_node(node, graph) -> tuple[MutationVariant, ...]`
- IN_SCOPE olmayan node için boş tuple döner (K1).
- Determinizm testi: aynı girdi → aynı varyant seti.

**Dosya**: `src/research_os/research/compiler.py` (adaptasyon, dokunmadan)
- `compile_experiment_intent` zaten `scope_derived` requirement'ını kabul ediyor; mutation varyantları bu requirement'ı taşıyan `http.transaction` intentleri üretir.
- **Yeni helper**: `research/mutation/intent.py` → `mutation_variant_to_intent(variant, budget_id) -> ExperimentIntent`.

**Testler**:
- `tests/unit/research/test_mutation_engine.py`
  - Her aile için determinizm testi.
  - UNKNOWN/OUT_OF_SCOPE node için boş varyant seti.
  - Provenance doğruluğu.
  - `MutationVariant → ExperimentIntent → ExperimentPlan` yolu validasyonu.

### P2 — OAST Çekirdeği

**Dosya**: `src/research_os/research/oast/types.py`
- **Sınıf**: `OastToken`
  - Alanlar: `token_id`, `research_run_id`, `hypothesis_id`, `target_reference`, `expires_at`, `created_at`.
- **Protokol**: `OastPort`
  - `mint_token(...) -> OastToken`
  - `poll_callback(token_id, *, before) -> tuple[OastCallback, ...]`
- **Sınıf**: `OastCallback`
  - Alanlar: `callback_id`, `token_id`, `received_at`, `raw_payload`, `headers`.

**Dosya**: `src/research_os/research/oast/loopback.py`
- **Sınıf**: `LoopbackOastPort(OastPort)`
  - Bellek içi token/callback store.
  - Süresi dolmuş token'a callback gelirse: ledger'a yazılır ama kanıt olarak kabul edilmez.

**Dosya**: `src/research_os/application/admit_oast_callback.py`
- **Use case**: `AdmitOastCallback`
  - Callback'i evidence hattına `UNTRUSTED_EXTERNAL` olarak taşır.
  - Stale token reddi.
  - Provenance korunur.

**Testler**:
- `tests/unit/research/test_oast_core.py`
  - Token üretim yaşam döngüsü.
  - Callback eşleştirme.
  - Stale callback reddi.
  - Admission sonrası `UNTRUSTED_EXTERNAL` korunur.

**Fixture**: `tests/fixtures/oast/`
- Loopback fixture kayıtları (örn. `callback_001.json`, `stale_callback.json`).

### P3 — Rate-Limit Enforcement

**Dosya**: `src/research_os/application/program_research_context.py`
- **Sınıf**: `ProgramPolicyView`
  - Yeni alan: `rate_limit_profile: RateLimitProfileRecord | None`
- **Fonksiyon**: `load_program_research_context`
  - Program'a ait rate limit profillerini `uow.rate_limit_profiles.list_for_program` ile çeker; ilkini view'a bağlar.
- **Fonksiyon**: `derive_loopback_only` dokunulmaz.

**Dosya**: `src/research_os/core/rate_limit.py` (yeni)
- **Sınıf**: `RateLimitCheck`
  - `allowed: bool`, `reason_code: ReasonCode`, `next_allowed_at: datetime | None`
- **Fonksiyon**: `check_rate_limit(profile, recent_attempts, now) -> RateLimitCheck`
  - `max_requests_per_window` / `window_seconds` bazlı.
  - Limit aşımında `ReasonCode.PROGRAM_POLICY_DENIED` veya yeni `RATE_LIMIT_DENIED` (eğer eklenirse).

**Dosya**: `src/research_os/core/enums.py`
- **Değişiklik**: Yeni `ReasonCode.RATE_LIMIT_DENIED` ekle (mevcut assert'leri etkilemez; yeni testler kullanır).

**Dosya**: `src/research_os/application/execute_planned_experiment.py`
- **Fonksiyon**: `authorize`
  - Core `evaluate_execution` çağrısından ÖNCE rate-limit kontrolü ekle.
  - Aşış varsa `ResearchLoopOutcome` DISPATCH_DENIED ile döner.
  - Audit event + ledger kaydı (BudgetConsumptionRecord `resource_type="RATE_LIMIT_DENIED"` veya audit event yeterli).

**Testler**:
- `tests/unit/application/test_execute_planned_experiment.py` (varsa) yeni testler.
- `tests/unit/core/test_rate_limit.py` yeni.
- Saat mock'lu deterministik test; sleep yok.

### P4 — Integration + Maturity

**Dosya**: `tests/integration/test_sd_g6_mutation_oast.py`
- PostgreSQL'li uçtan uca:
  - census → admission → graf → mutation varyant üretimi → ledger.
  - OAST loopback callback → evidence admission.
  - rate-limit uçtan uca DENY.

**Dosya**: `src/research_os/maturity.py`
- Yeni: `GATE_06_STATUS = "PENDING"`
- Docstring paragrafı ekle: "SD-G6 = Mutation Engine + OAST Core + Rate-Limit Enforcement; eski GATE 06 değildir."

**Dosya**: `OPERATIONS.md`
- SD-G6 bölümü: mutation aileleri listesi, OAST token yaşam döngüsü, rate-limit zorlaması, loopback-only test garantisi.

**Alembic**: `alembic/versions/a30_001_mutation_oast.py`
- Yeni tablolar (öneri):
  - `mutation_variant` (opsiyonel; varyantlar ledger'da tutulabilir).
  - `oast_token`
  - `oast_callback`
  - `hunt_v3_queue` zaten var; `mutation_queue` gerekirse.
- Eğer varyantlar sadece runtime üretilecekse tablo eklemeden `audit_event` payload'ına yazılabilir.

> **Karar**: Varyantlar append-only `audit_event` + geçici runtime listesi olarak tutulur; ayrı tablo eklenmez (SoR şişmesin). OAST token/callback için kalıcı tablo eklenir çünkü kanıt zinciri gerektirir.

## 5. UYGULAMA SIRASI

1. **P0**: `_enqueue_v3` IN_SCOPE kilidi + unit testi.
2. **P3**: `ProgramPolicyView` rate_limit_profile + `core/rate_limit.py` + `execute_planned_experiment.py` kontrolü + unit testleri.
3. **P1**: Mutation engine modülü + unit testleri.
4. **P2**: OAST core + loopback implementasyonu + unit testleri.
5. **P4**: Integration testleri + `maturity.py` PENDING + `OPERATIONS.md` SD-G6 bölümü.
6. Her aşamada `pytest tests/unit tests/contract -q` yeşil kalır.
7. Son: Kali + PostgreSQL'de full suite yeşil; commit + push.

## 6. KAPANIŞ STANDARDI

- `GATE_06_STATUS = "PENDING"` + docstring.
- `OPERATIONS.md` SD-G6 bölümü.
- Unit+contract: 1038+ PASS, sıfır silinen test.
- Integration: mutation varyant → ledger; OAST loopback → evidence; rate-limit DENY uçtan uca.
- Mühür bende: push + bağımsız denetim olmadan PASS yazılmaz.
