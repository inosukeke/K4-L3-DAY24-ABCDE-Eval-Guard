# Blueprint CI/CD cho RAG và guardrails

Nhóm: ABCDE.

Người phụ trách blueprint: Nguyễn Đình Khang - 2A202602584

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy. Evidence đã lưu gồm `artifacts/ragas_50q.json`, `artifacts/judge_results.json` và `artifacts/guard_results.json`. Lần chạy guard gần nhất có timestamp `2026-10-12T14:40:45.162599+00:00`; guard model là `gpt-4o-mini`. Theo metadata của A/B, generation dùng `qwen/qwen3.8-27b`, evaluator ghi `BAAI/bge-m3` và `qwen/qwen3.8-27b`, còn judge dùng `gpt-4o-mini`.

## Kiến trúc và failure action

Luồng đề xuất là: **Input → Presidio → NeMo input → RAG → NeMo output → response**. Presidio chỉ dùng các entity có thể hành động trong policy lab (`VN_CCCD`, `VN_PHONE`, `EMAIL_ADDRESS`, `PHONE_NUMBER`); recognizer `PERSON` tiếng Anh không dùng để block vì gây false positive trên câu tiếng Việt. Nếu Presidio phát hiện PII, request dừng ở lớp này và chỉ text đã anonymize cùng loại entity/vị trí được ghi log. Nếu không, NeMo input rail kiểm tra jailbreak, off-topic, impersonation, prompt extraction và yêu cầu dữ liệu/credential bí mật.

Request thực có thể dừng sớm ở Presidio hoặc NeMo input. Nếu qua input guard, pipeline RAG mới retrieve/generate; NeMo output rail kiểm tra answer trước khi trả về. Output bị gắn cờ được thay bằng refusal, còn output an toàn được giữ nguyên. Lần chạy thật đã chặn đúng 20/20 attacks, cho phép 8/8 clean inputs và xử lý đúng 4/4 output cases; 4 input bị chặn bởi Presidio, 16 bởi NeMo input.

Secrets chỉ nên ở `.env` hoặc secret manager; không log API key, raw PII, retrieved contexts nhạy cảm hay credential. Đề xuất khi provider/rail không sẵn sàng là fail closed với refusal ngắn, gắn request ID và alert vận hành; đây là failure action đề xuất, chưa phải workflow CI/CD đã triển khai. Với generation fallback, cần ghi rõ `generation_mode` và không trình bày answer extractive như lời gọi LLM thành công.

## Phạm vi và số đo latency

Task 12 đo đúng scope `input_layers_sequential`: Presidio rồi NeMo input trên cùng mỗi sample, không short-circuit dù input có thể bị block trong request thật. Engines được tạo trước khi đo; 2 warm-up thật bị loại khỏi kết quả. Có 20 timed samples, raw milliseconds được lưu trong `guard_results.json`; percentile dùng nội suy tuyến tính tại `(n - 1) × q`.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---:|---:|---:|---|
| Presidio | 10.86 | 13.28 | 13.51 | Đã đo, thấp hơn budget input-layer |
| NeMo input | 697.08 | 803.86 | 816.76 | Đã đo; là bottleneck chính |
| Input guard sequential | 707.82 | 815.38 | 825.79 | Đã đo; vượt target 500ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi Task 12 |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi Task 12 |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input guard sequential |

`latency_budget_ok` là `false`: P95 input guard 815.38ms vượt 500ms. Không thể dùng số này để kết luận P95 của RAG, output rail hoặc end-to-end request. Bước cải thiện có thể kiểm tra tiếp theo là đo riêng NeMo input theo provider/model, sau đó đo full request với cùng warm-up, số samples và request mix được ghi rõ.

## CI gates đề xuất

- Giữ mốc bắt buộc lab: attacks ít nhất 15/20, clean 8/8 allowed, false-positive rate bằng 0 và 4 output cases đúng expected. Evidence hiện tại đạt 20/20 attacks, 8/8 clean và 4/4 outputs.
- Dùng attacks ít nhất 18/20 cùng clean 8/8 như CI gate đề xuất; lần chạy hiện tại đạt 20/20.
- Dùng RAGAS faithfulness ít nhất 0.75 và `avg_score` ít nhất 0.65 trên 50 câu như ngưỡng đề xuất. Lần A hiện có factual 0.8365, multi-hop 0.6480 và adversarial 0.6897 theo `avg_score`; multi-hop chưa đạt ngưỡng đề xuất.
- Chỉ áp dụng gate P95 dưới 500ms cho input layers sau khi đã đo đúng scope này; kết quả hiện tại chưa đạt. Không áp ngưỡng đó cho full guard trước khi có phép đo full guard.
- Job đề xuất chạy unit tests offline trước, sau đó tạo/validate artifacts thật và trả nonzero nếu gate được cấu hình không đạt. Đây là kế hoạch CI/CD, chưa phải pipeline đã được triển khai.

## Monitoring và cải tiến

Theo dõi theo từng run: attack pass rate, clean false-positive rate, output safety pass rate, từng `blocked_by`, raw latency samples/P50/P95/P99 và lỗi provider. Log chỉ nên chứa request ID, loại policy/entity, quyết định và latency; dùng anonymized text khi cần debug. Alert khi clean false-positive rate lớn hơn 0, attacks dưới 15/20 hoặc P95 input guard vượt 500ms. Bộ 20/8/4 là nhỏ, vì vậy alert cần kích hoạt review case chứ không tự kết luận drift.

RAGAS cho thấy `answer_relevancy` là worst metric ở 49 câu và multi-hop là distribution yếu nhất. Ưu tiên kiểm chứng tăng `top_k` và reranker thật cho câu multi-hop, sau đó chạy lại A trên cùng test set. Cohen's kappa của 10 model answers là 1.0, nhưng mẫu calibration nhỏ nên cần mở rộng nhãn người trước khi xem judge là đủ tin cậy. Adversarial RAGAS mean 0.6897 thấp hơn factual 0.8365; tiếp tục tách policy version cũ/mới và các câu phủ định trong retrieval evaluation.

Các cải tiến đề xuất có thể kiểm tra được là: (1) benchmark provider/model của NeMo input để hạ P95, (2) thêm regression cases tiếng Việt cho password version và off-topic trước mọi thay đổi prompt, (3) theo dõi false positives của Presidio theo entity type thay vì bật recognizer `PERSON` mù quáng, (4) đánh giá reranker/top-k bằng chênh lệch multi-hop `avg_score`, và (5) mở rộng calibration judge với câu diễn đạt mơ hồ cùng nhãn người.
