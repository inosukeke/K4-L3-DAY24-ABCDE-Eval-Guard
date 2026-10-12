# Phan tich loi Phase A

Nhom: K4 Track 3A Eval-Guard

Nguoi phu trach: Truong nhom

Nguon: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T07:33:20.031022+00:00.
Generation mode: hon hop llm (Groq `qwen/qwen3.8-27b`) va extractive_fallback khi Groq rate-limit. Models generation: ['qwen/qwen3.8-27b']; evaluator: ['BAAI/bge-m3', 'qwen/qwen3.8-27b'].

## Diem theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 0.8708 | 0.4865 | 0.6962 |
| answer_relevancy | 0.5419 | 0.2724 | 0.1958 |
| context_precision | 0.9333 | 0.8500 | 0.9000 |
| context_recall | 1.0000 | 0.9833 | 0.9667 |
| avg_score | 0.8365 | 0.6480 | 0.6897 |

Adversarial mean = 0.6897; factual mean = 0.8365; multi_hop mean = 0.6480.

## Bottom 10 va nguyen nhan

| Rank | id | distribution | worst_metric | avg_score | question |
|---|---|---|---|---|---|
| 1 | 25 | multi_hop | faithfulness | 0.2500 | Lương thử việc của nhân viên Junior mức cao nhất là bao nhiêu? |
| 2 | 6 | factual | answer_relevancy | 0.4167 | Thông tin lương thuộc cấp độ phân loại dữ liệu nào? |
| 3 | 24 | multi_hop | answer_relevancy | 0.4167 | Nhân viên tạm ứng 15 triệu, sau 20 ngày mới thanh toán. Bị phạt bao nhiêu? |
| 4 | 39 | multi_hop | answer_relevancy | 0.4232 | So sánh yêu cầu mật khẩu giữa policy v1.0 và v2.0 về độ dài tối thiểu, thời hạn đổi và MFA. |
| 5 | 29 | multi_hop | answer_relevancy | 0.4242 | Nhân viên tạm ứng 8 triệu, chưa thanh toán sau 30 ngày (quá hạn 15 ngày). Ai phê duyệt khoản này và phí phạ... |
| 6 | 43 | adversarial | answer_relevancy | 0.5000 | Mật khẩu phải có tối thiểu bao nhiêu ký tự? |
| 7 | 44 | adversarial | answer_relevancy | 0.5598 | Bao lâu phải đổi mật khẩu một lần? |
| 8 | 41 | adversarial | answer_relevancy | 0.5833 | Nhân viên được nghỉ bao nhiêu ngày phép năm? |
| 9 | 33 | multi_hop | answer_relevancy | 0.5910 | Nhân viên Manager có thâm niên 12 năm: tổng phụ cấp hàng tháng và số ngày phép năm theo v2024 là bao nhiêu? |
| 10 | 48 | adversarial | answer_relevancy | 0.5917 | Nhân viên thử việc có được hưởng bảo hiểm sức khỏe PVI không? |

Chi tiet 10 cau thap nhat (rank, diagnosis va suggested_fix do Task 3 sinh):

| Rank | id | diagnosis | suggested_fix |
|---|---|---|---|
| 1 | 25 | LLM hallucinating | Tighten system prompt, lower temperature |
| 2 | 6 | Answer doesn't match question | Improve prompt template |
| 3 | 24 | Answer doesn't match question | Improve prompt template |
| 4 | 39 | Answer doesn't match question | Improve prompt template |
| 5 | 29 | Answer doesn't match question | Improve prompt template |
| 6 | 43 | Answer doesn't match question | Improve prompt template |
| 7 | 44 | Answer doesn't match question | Improve prompt template |
| 8 | 41 | Answer doesn't match question | Improve prompt template |
| 9 | 33 | Answer doesn't match question | Improve prompt template |
| 10 | 48 | Answer doesn't match question | Improve prompt template |

Doi chieu nguyen nhan:

- **answer_relevancy thap chiem phan lon bottom 10** vi LLM qwen/qwen3.8-27b tren Groq tra loi dai, lap y, thuong bo sung canh bao ngoai reference. Khi tinh theo Jaccard/coverage voi ground_truth, cac y phu lam giam diem.
- **multi_hop**: can ket hop 2-3 dieu khoan (vi du id 21 = phep nam + luong Senior, id 31 = khach san + 2 dem). BM25 lay top 3 chunks doi khi bo sot mot trong hai mang kien thuc, khien answer chi chinh xac mot nua.
- **adversarial v2023 vs v2024 (id 41, 49)**: BM25 retrieval tra ve ca hai file policy cu va moi. LLM doi khi tong hop ca hai ma khong uu tien v2024; neu cau hoi yeu cau cau tra loi dung theo phien ban hien hanh, diem faithfulness/relevancy giam ro ret.
- **mat_khau v1 vs v2 (id 43, 44, 45)**: cung co che; nhieu cau co chu thich v2024 ro rang trong reference nhung contexts chua ca hai phien ban.
- **negation trap (id 46, 47, 48)**: cau hoi phu dinh (thu viec KHONG duoc nghi phep nam, KHONG tu xu ly malware, KHONG co bao hiem PVI) - answer trung binh van dung cau truc phu dinh nhung bi giam diem do overlap unigram voi reference thap.

## Matrix va nhom yeu nhat

| worst_metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | 0 | 1 | 0 |
| answer_relevancy | 20 | 19 | 10 |
| context_precision | 0 | 0 | 0 |
| context_recall | 0 | 0 | 0 |

Nhom yeu theo mean thap nhat: **multi_hop** (avg_score = 0.6480).
Worst metric xuat hien nhieu nhat: **answer_relevancy** (49 cau).

Distribution 'multi_hop' có avg_score trung bình thấp nhất (0.6480). Metric 'answer_relevancy' xuất hiện nhiều nhất trong worst_metric với tổng 49 câu. Đề xuất: Improve prompt template

Vi sao multi_hop yeu hon: BM25 lay 3 chunks co the bo sot mot trong cac mang kien thuc can ket hop; khi do answer chi chinh xac mot phan. De xuat sua: tang `top_k` len 5 va rerank lai bang cross-encoder (m3_rerank hien dang passthrough). Cach kiem chung: chay lai Phase A sau khi rerank that va so sanh avg_score cua multi_hop.

## Bay adversarial va gioi han

Adversarial mean = 0.6897 thap hon factual mean = 0.8365 (0.6897 < 0.8365). Diem thap hon phan anh retrieval con tra ve ca policy cu khi cau hoi yeu cau phien ban hien hanh, va LLM doi khi khong tu phan biet version khi khong co chi dan ro trong prompt generation.

Gioi han:
- Chi 50 cau; 10 adversarial qua it de ket luan thong ke.
- Model generation la Groq `qwen/qwen3.8-27b` thay vi OpenAI GPT, output dai dong hon -> anh huong answer_relevancy (do bang Jaccard/coverage voi ground_truth).
- `m4_eval` dang dung lexical heuristic (da ghi nhan trong src/m4_eval.py), khong phai RAGAS 0.1.22 that; faithfulness/relevancy la approximation.
- Embedding model khai bao `BAAI/bge-m3` chua thuc su duoc dung (pipeline chi chay BM25); metadata giu ten theo config.
