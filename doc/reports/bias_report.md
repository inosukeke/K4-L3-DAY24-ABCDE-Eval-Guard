# Đánh giá LLM Judge Phase B

Nhóm: ABCDE

Người phụ trách: Trần Hữu Đức — 2A202602459

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T08:29:53.060896+00:00.
Models generation/judge: metadata.models.generation = ["qwen/qwen3.8-27b"]; metadata.models.judge = ["gpt-4o-mini"].

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

| id | A (nguồn pipeline) | B (model_answer) | winner_pass1 | winner_pass2 | final_winner | position_consistent | scores_pass1 (A/B) | scores_pass2 (A/B) |
|---|---|---|---|---|---|---|---|---|
| 1 | "Nhân viên được nghỉ 3 ngày làm việc khi kết hôn." | "Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn." | B | B | **B** | true | 0.7 / 1.0 | 0.8 / 1.0 |
| 5 | "Tổng Giám đốc (CEO)" | "Cần Giám đốc phòng ban phê duyệt." | A | A | **A** | true | 1.0 / 0.0 | 1.0 / 0.2 |
| 12 | "...tối thiểu **1 tháng lương**." | "Nhân viên được thưởng Tết tối thiểu 1 tháng lương." | A | A | **A** | true | 1.0 / 0.7 | 1.0 / 0.8 |
| 21 | "...18 ngày phép năm... không thể xác định lương..." | "Được nghỉ 18 ngày phép (15+3). Lương Senior từ 20 đến 35 triệu." | B | B | **B** | true | 0.6 / 1.0 | 0.7 / 1.0 |
| 41 | "Không tìm thấy." | "Nhân viên được nghỉ 12 ngày phép năm." | B | A | **tie** | false | 0.0 / 0.5 | 0.5 / 0.0 |

Position bias count/rate: 1/5 = 0.2.
Verbosity win rate: 0.5; decisive cases: 4 (id 1, 5, 12, 21; id 41 là tie nên không tính vào decisive).

Case không nhất quán duy nhất là id 41: pass 1 (thứ tự A=pipeline, B=human) chọn B
("12 ngày phép") vì A ("Không tìm thấy") không có thông tin; pass 2 (thứ tự đã đảo)
chấm lại raw winner="A" (tức sau quy đổi là B gốc thắng ở pass 2 raw, nhưng sau convert
về không gian A/B ban đầu kết quả là winner_pass2="A") — judge đổi lựa chọn giữa hai
lượt. Đây là bằng chứng **thống kê** của vị trí không ổn định trên câu hỏi có cả hai
answer đều sai/thiếu (A từ chối trả lời, B dùng chính sách cũ v2023 — 12 ngày thay vì
15 ngày v2024). Không đủ để khẳng định đây là "position bias hệ thống" của model: với
2 answer cùng mức độ sai, model có thể dao động quyết định theo nội dung chứ không chỉ
theo vị trí; cần nhiều case như vậy hơn 5 cặp mới kết luận chắc.

Verbosity win rate 0.5 nằm trong 4 case decisive: id 1 (B thắng, B dài hơn A) và id 21
(B thắng, B dài hơn A) ủng hộ answer dài hơn; id 5 (A thắng, A ngắn hơn B) và id 12
(A thắng, A dài hơn B một chút) thì một case verbosity đi theo A ngắn hơn — vẫn thắng.
Đọc nội dung cho thấy: id 1 và 21, answer dài hơn thắng vì **chứa thêm thông tin đúng
và cần thiết** (lương, tình trạng có lương), không phải vì dài đơn thuần. Id 5, answer
ngắn hơn (A="CEO") thắng vì đúng chính xác chức danh phê duyệt, còn answer dài hơn (B)
lại sai chức danh. Kết luận: verbosity win rate 0.5 là dấu hiệu thống kê trung tính
(dưới ngưỡng >0.6 cảnh báo của hàm bias_report), và khi đọc nội dung thì các case thắng
đều có lý do nội dung hợp lý, không phải judge chỉ chọn theo độ dài.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

| question_id | model_answer (gốc) | nhãn judge (0/1) | reasoning (rút gọn) | human_label | agree |
|---|---|---|---|---|---|
| 1 | "Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn." | 1 | Đúng, nêu rõ số ngày và điều kiện không trừ phép năm. | 1 | ✓ |
| 5 | "Cần Giám đốc phòng ban phê duyệt." | 0 | Sai người phê duyệt, cần Tổng Giám đốc không phải Giám đốc phòng ban. | 0 | ✓ |
| 12 | "Nhân viên được thưởng Tết tối thiểu 1 tháng lương." | 1 | Đúng theo reference, nêu rõ điều kiện và mức thưởng. | 1 | ✓ |
| 21 | "Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu." | 1 | Đúng cả số ngày phép và khoảng lương Senior. | 1 | ✓ |
| 23 | "Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết." | 1 | Đúng, hoàn trả 25 triệu do chưa đủ 1 năm cam kết. | 1 | ✓ |
| 29 | "Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu." | 0 | Thiếu phê duyệt Kế toán trưởng; phạt tính sai (không pro-rata 15 ngày). | 0 | ✓ |
| 33 | "Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng." | 1 | Đúng cả số ngày phép và tổng phụ cấp theo tài liệu. | 1 | ✓ |
| 41 | "Nhân viên được nghỉ 12 ngày phép năm." | 0 | Dùng chính sách cũ v2023; v2024 hiện hành là 15 ngày. | 0 | ✓ |
| 46 | "Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần." | 1 | Đúng hoàn toàn, nêu cả hành động thay thế. | 1 | ✓ |
| 50 | "Được, miễn là đảm bảo kết nối an toàn." | 0 | Sai, chính sách VPN v1.3 cấm VPN cá nhân, phải dùng VPN công ty. | 0 | ✓ |

Cohen's κ: **1.0**.
Observed agreement = 10/10 = 1.0; chance agreement = (6/10)² + (4/10)² = 0.36 + 0.16 = 0.52;
κ = (1.0 − 0.52) / (1 − 0.52) = 0.48/0.48 = **1.0** — đồng thuận hoàn hảo giữa judge
(gpt-4o-mini) và 10 nhãn người trên chính bộ `human_labels_10q.json`, không có lệch nhãn
nào trong 10 câu này.

## Giới hạn và cách dùng judge

Judge model: `gpt-4o-mini` (JUDGE_MODEL, qua proxy OpenAI-compatible); binary helper dùng
cùng model qua `src.experiment_support.judge_binary`. Prompt pairwise có 3 tiêu chí
(accuracy/completeness/conciseness); prompt binary chỉ nhận question/answer/reference,
không có nhãn/tỷ lệ human.

Mẫu rất nhỏ: chỉ 5 cặp pairwise và 10 nhãn binary — κ=1.0 trên 10 mẫu không chứng minh
judge luôn đúng trên 50 câu hoặc trên domain khác; sai số chuẩn của κ với n=10 lớn, một
nhãn lệch sẽ kéo κ xuống đáng kể (κ ước tính nhạy với mẫu nhỏ). Cả 10 case binary đều
rơi vào loại lỗi rõ ràng (sai số tiền, sai cấp phê duyệt, dùng version cũ), là loại lỗi
dễ phát hiện bằng cách so khớp từ khóa với reference — chưa kiểm chứng judge trên các
case mơ hồ hơn (diễn đạt khác nhưng vẫn đúng ý, bán đúng bán sai).

Không có case lệch nhãn với human trong 10 câu này ở lần chạy này; nếu mở rộng tập nhãn,
cần tiếp tục đối chiếu từng case lệch bằng cách đọc answer/reference, không chỉ nhìn κ.
Judge không được xem là đáp án tuyệt đối: dùng để sàng lọc nhanh và gắn cờ case nghi
ngờ, quyết định cuối với case tranh chấp (ví dụ id 41 — cả A và B đều có vấn đề) vẫn cần
người đọc trực tiếp contexts và reference trước khi tin kết quả.
