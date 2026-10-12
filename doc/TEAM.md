# Nhóm thực hiện ABCDE — K4 Track 3A Eval-Guard

Tên nhóm: ABCDE

Repo chung: https://github.com/inosukeke/K4-L3-DAY24-ABCDE-Eval-Guard.git

Trưởng nhóm/người nộp: Nguyễn Đình Khang — 2A202602584.

Ngày lab/deadline áp dụng: 12/10/2026, 23:59 — Asia/Ho_Chi_Minh (UTC+07:00), theo deadline mặc định và các cập nhật của coach nếu có.

Commit dùng để chấm: chưa tạo tại thời điểm điền tài liệu. Trước khi nộp, trưởng nhóm sẽ commit toàn bộ thay đổi đã kiểm tra, thay dòng này bằng SHA commit cuối và gửi đúng SHA đó cho coach.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Bùi Gia Chính | 2A202602693 | Phase A: RAGAS evaluation, failure clustering và báo cáo lỗi | `artifacts/ragas_50q.json`, `doc/reports/failure_clusters.md`, commit `db02d3e` |
| 2 | Trần Hữu Đức | 2A202602459 | Phase B: pairwise/binary LLM judge, calibration và bias report | `artifacts/judge_results.json`, `doc/reports/bias_report.md`, commit `1a42f1d` |
| 3 | Nguyễn Đình Khang | 2A202602584 | Phase C: Presidio/NeMo guardrails, latency, blueprint; tích hợp và nộp bài | `artifacts/guard_results.json`, `doc/reports/blueprint.md`, thay đổi local chờ commit |

Người tích hợp/chạy batch/nộp link: Nguyễn Đình Khang. Đã chạy checker, refresh Phase A theo answers hiện tại, chạy Phase C live và sẽ tạo commit nộp sau khi kiểm tra `.DS_Store`/secrets.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: macOS Apple Silicon; Python 3.11.17 trong `.venv`. Annoy và các dependency full runtime đã import được; compiler hệ điều hành không được ghi riêng trong artifact.

Virtualenv/dependencies/imports: `python -m pip check` báo không có broken requirements. Lệnh import `ragas`, `nemoguardrails`, `presidio_analyzer` và `spacy` thành công. Offline suite gần nhất đạt 86 passed, 3 deselected.

Models/Qdrant/50 answers đã chuẩn bị: `artifacts/answers_50q.json` hợp lệ với 50 answers LLM dùng `qwen/qwen3.8-27b`. Phase A ghi evaluator `BAAI/bge-m3` và `qwen/qwen3.8-27b`; Phase B/Phase C dùng `gpt-4o-mini` theo metadata. Pipeline hiện có BM25 fallback trong M2; không dùng unit test để khẳng định Qdrant/full production retrieval đã được benchmark riêng.

## INDIVIDUAL

### BuiGiaChinh-2A202602693

- Phần được giao và phần thực tế đã làm: Phase A trong `src/phase_a_ragas.py`: nhóm 50 câu theo distribution, gọi adapter M4 để tạo `RagasEvaluation`, chọn bottom 10, tạo matrix theo `worst_metric` và phân tích failure clusters.
- Bằng chứng: `artifacts/ragas_50q.json` có 50 `per_question`, ba summaries 20/20/10 và metadata evaluator; `doc/reports/failure_clusters.md`; commit Phase A `db02d3e`.
- Cách kiểm tra: chạy `python -m pytest tests/test_phase_a.py -q`, sau đó chạy evaluation trên `artifacts/answers_50q.json`; checker cuối xác nhận Phase A artifact hợp lệ. Lần run hiện lưu timestamp `2026-10-12T14:26:21.685165+00:00`.
- Điều đã học: điểm RAGAS/metric thấp chỉ là tín hiệu để đọc question, answer, contexts và reference; không được suy ngay metric thấp nhất là lỗi của một module duy nhất. Nhóm yếu phải chọn theo mean của distribution, không theo số lượng câu.
- Giới hạn/cách xử lý: `m4_eval` hiện là lexical heuristic nên các metric là approximation, đồng thời multi-hop dễ thiếu một phần contexts khi BM25 chỉ lấy ít chunks. Báo cáo giữ nguyên giới hạn này và đề xuất tăng `top_k`/rerank thật rồi chạy lại Phase A để so sánh.
- Nguồn/AI hỗ trợ nếu có: Codex hỗ trợ đối chiếu contract, tích hợp/checker và rà soát report; kết quả được tự kiểm chứng bằng tests, JSON artifact và đọc các bottom cases.

### TranHuuDuc-2A202602459

- Phần được giao và phần thực tế đã làm: Phase B trong `src/phase_b_judge.py`: thực hiện pairwise judge cho 5 cặp cố định theo hai thứ tự A/B và B/A, quy winner về A/B gốc, chấm 10 `model_answer` theo binary judge, tính Cohen's κ và báo cáo position/verbosity bias.
- Bằng chứng: `artifacts/judge_results.json`, `doc/reports/bias_report.md`, commit Phase B `1a42f1d`. Artifact lưu 10 lượt pairwise, 10 binary judgments và provenance model judge `gpt-4o-mini`.
- Cách kiểm tra: chạy `python -m pytest tests/test_phase_b.py -q`, rồi chạy runner Phase B live; checker cuối xác nhận artifact Phase B, `pair_sources`, IDs và calibration hợp lệ. Kết quả lưu timestamp `2026-10-12T08:29:53.060896+00:00`.
- Điều đã học: winner A/B của pairwise không phải nhãn đúng/sai để tính calibration; cần swap hai lượt và quy đổi winner về danh tính candidates ban đầu. Cohen's κ phải dùng đúng 10 `model_answer` có nhãn người, cùng IDs và thứ tự.
- Giới hạn/cách xử lý: mẫu pairwise chỉ có 5 cặp và calibration chỉ 10 câu; κ=1.0 không đủ để kết luận judge luôn đáng tin. Báo cáo tách position inconsistency ở id 41 khỏi kết luận bias hệ thống và đề xuất mở rộng tập câu mơ hồ/khác phiên bản.
- Nguồn/AI hỗ trợ nếu có: Codex hỗ trợ đối chiếu contract, tích hợp/checker và rà soát report; kết quả được tự kiểm chứng bằng tests, JSON artifact và so sánh trực tiếp answer/reference.

### NguyenDinhKhang-2A202602584

- Phần được giao và phần thực tế đã làm: Phase C trong `src/phase_c_guard.py`; implement PII scan, input/output NeMo rails, adversarial suite, latency; sửa false positive `PERSON` trên tiếng Việt và bổ sung policy regression cho password version/off-topic. Đồng thời cập nhật `guardrails/config.yml` và `doc/reports/blueprint.md`.
- Bằng chứng: `artifacts/guard_results.json` chạy live lúc `2026-10-12T14:40:45.162599+00:00`; attacks 20/20, clean 8/8, output 4/4. Blueprint ghi P95 input guard 815.38ms và `latency_budget_ok=false`.
- Cách kiểm tra: `python -m pytest tests/test_phase_c.py -q` đạt 12 tests; checker với tests offline đạt 86 passed, 3 deselected và Phase C artifact pass.
- Điều đã học: cần đo input layers tuần tự bằng raw samples, tách kết luận latency input khỏi RAG/output/end-to-end; cũng cần kiểm soát false positive của recognizer theo loại entity.
- Giới hạn/cách xử lý: P95 input guard vượt budget 500ms; blueprint đề xuất benchmark provider/model của NeMo input và mở rộng regression cases trước khi coi latency gate là đạt.
- Nguồn/AI hỗ trợ nếu có: Codex hỗ trợ triển khai/debug Phase C, kiểm tra contract và soạn blueprint; các thay đổi được kiểm chứng lại bằng unit tests, checker và live artifact.

## Cập nhật sau khi nộp

Chưa có cập nhật sau nộp. Trước lần nộp đầu tiên, trưởng nhóm cần thay dòng commit dùng để chấm bằng SHA commit cuối, kiểm tra artifact không bị ignore, không commit `.env`/API key/`.DS_Store`, và mở đúng commit trên GitHub.
