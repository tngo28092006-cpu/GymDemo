# GYM / CNPM — Quản lý phòng tập

Ứng dụng thử nghiệm Flask + SQLite, giao diện tiếng Việt, dùng trong PyCharm.

## Chạy lần đầu

1. Mở thư mục dự án bằng PyCharm, chọn Python interpreter (Python 3.10 trở lên).
2. Trong Terminal: `python -m pip install -r requirements.txt`.
3. Run `index.py`, hoặc chạy `python index.py`. Cấu hình Flask của PyCharm (`flask run`) cũng được hỗ trợ.
4. Mở http://127.0.0.1:5000.

Không mở các file HTML trực tiếp. Database `gym.db` tự tạo/cập nhật khi khởi động; chạy lại không mất dữ liệu.
Không cần Node hay bước build. Sau cập nhật, chạy lại Flask và nhấn Ctrl+F5 để tải CSS/JS mới.
Sao lưu `gym.db` trước nâng cấp; không xóa file này hoặc đưa dữ liệu hội viên lên GitHub.

## Tài khoản và vai trò

Database mới tạo `admin` và `letan`, mật khẩu mặc định `Gym@12345`.
Có thể đặt biến môi trường `DEMO_PASSWORD` trước lần chạy đầu để thay mật khẩu khởi tạo.
Tài khoản đang có giữ mật khẩu cũ khi cập nhật.

- Admin: báo cáo, quy định, thanh toán, quản lý hội viên và tạo/xóa HLV; không xếp lịch.
- Lễ tân: quản lý hội viên, thu tiền, đặt lại mật khẩu hội viên, tạo/xóa HLV.
- HLV: do admin/lễ tân tạo ở Quản lý HLV, nhận yêu cầu và lập/xóa lịch cho hội viên đã xác nhận.
- Hội viên: tạo tài khoản tại `/signup`, đăng nhập bằng số điện thoại và mật khẩu; email tùy chọn.

Không tạo HLV mặc định trên database mới. HLV cũ được giữ; tài khoản thu ngân cũ chuyển thành quyền lễ tân.
Tên đăng nhập HLV cần 3–40 ký tự, bắt đầu bằng chữ, có thể chứa số và dấu `.`, `_`, `-`.
Mật khẩu 8–128 ký tự, lưu dạng băm. Không hiển thị mật khẩu đã lưu.

## Ba trang hội viên

- **Trang chủ** (`/account`): lịch tập đang hoạt động, gói đang dùng, ngày đăng ký gói, ngày bắt đầu, ngày hết hạn và số ngày còn lại.
- **Thông tin** (`/account/info`): hồ sơ, ngày tạo tài khoản, email, đổi mật khẩu và đăng ký/hủy HLV.
- **Đăng ký gói tập** (`/account/packages`): danh mục gói, đăng ký/gia hạn và lịch sử hóa đơn.

Ngày đăng ký gói là ngày lập hóa đơn, khác ngày tạo hồ sơ tài khoản.
Số ngày còn lại = ngày hết hạn trừ ngày hiện tại, không âm; ngày hết hạn là ngày đầu tiên không còn hiệu lực.
Gói chưa thanh toán hiện Chờ kích hoạt, chưa tính ngày; gói tương lai hiện Chưa đến ngày bắt đầu.
Tạo tài khoản chưa tạo hóa đơn. Mỗi hội viên chỉ có một hóa đơn chờ; giá đã lập được giữ nguyên.
Hóa đơn thanh toán xong mới kích hoạt gói và tính doanh thu; gói gia hạn bắt đầu sau gói đã thanh toán trước đó.
Các POST `/account` cũ vẫn được hỗ trợ và chuyển về trang liên quan.

## Luồng HLV

1. Admin/lễ tân tạo tài khoản HLV tại Quản lý HLV.
2. Hội viên vào Thông tin, chọn HLV và gửi yêu cầu; lễ tân/admin cũng có thể hỗ trợ gửi tại quầy.
3. HLV vào Yêu cầu HLV để xác nhận hoặc từ chối. Chỉ HLV được chọn mới xử lý yêu cầu.
4. Sau xác nhận, hội viên xuất hiện trong danh sách riêng của HLV và mới được xếp lịch.
5. Hội viên được hủy yêu cầu chờ hoặc hủy đăng ký đã được nhận qua trang xác nhận.

Hủy đăng ký đã nhận sẽ bỏ liên kết và ngừng lịch hiện tại, giữ lịch sử, gói Gym và hóa đơn.
Hội viên có thể chọn HLV mới và chờ xác nhận mới. HLV chỉ xem và xếp lịch cho hội viên của mình.
Trang chính HLV là bảng lịch đã xếp, không có doanh thu hoặc biểu đồ đăng ký theo tháng.
Quy định ngày tập áp dụng trên tổng số ngày khác nhau của mọi bài tập đang hoạt động mỗi hội viên.

## Mật khẩu và xóa hồ sơ

Hội viên vào Thông tin > Đổi mật khẩu, cần mật khẩu hiện tại.
Admin/lễ tân đặt lại mật khẩu hội viên ở Hội viên, xác nhận bằng mật khẩu của chính nhân viên thao tác.
Đổi/reset mật khẩu chặn mọi phiên cũ ở lần truy cập tiếp theo.

Xóa hội viên/HLV có trang xác nhận. Hồ sơ được ẩn/khóa thay vì xóa lịch sử thanh toán.
Xóa HLV hủy liên kết/yêu cầu và dừng lịch của hội viên đang thuộc HLV đó; các HLV khác không bị ảnh hưởng.
Số điện thoại hoặc tên HLV đã xóa có thể tạo tài khoản mới với ID riêng, không nhận dữ liệu cũ.
Hồ sơ tại quầy chưa gắn tài khoản cần hỗ trợ riêng; chưa có giao diện kích hoạt tài khoản cho hồ sơ cũ.

## SMTP tùy chọn

Trong PyCharm > Run > Edit Configurations > Environment variables:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=email-cua-ban@gmail.com
SMTP_USER=email-cua-ban@gmail.com
SMTP_PASSWORD=mat-khau-ung-dung
SECRET_KEY=chuoi-ngau-nhien-dai-cua-ban
```

Dùng mật khẩu ứng dụng của nhà cung cấp email. Không đưa thông tin SMTP vào code hoặc GitHub.
Không có email thì bỏ qua SMTP. Chưa cấu hình hoặc gửi lỗi vẫn lưu đăng ký và báo rõ trên giao diện.
Email chỉ gửi khi đăng ký gói thành công; không gửi khi khởi động hoặc đổi mật khẩu.

## Giao diện và kiểm tra

Sidebar theo vai trò, menu co gọn trên điện thoại, bảng cuộn trong khung và tìm nhanh hỗ trợ không dấu.
Biểu đồ dùng Chart.js từ CDN; khi không tải được, mở bảng số liệu chi tiết để xem.
Kiểm tra: `python -m unittest discover -s tests -v`.

Đây là bản demo localhost. Chưa có OTP, tự khôi phục mật khẩu hoặc giới hạn thử đăng nhập.
Trước triển khai công khai cần bổ sung HTTPS, bảo vệ đăng nhập, sao lưu và quản lý tài khoản đầy đủ.

### Nâng gói trong 3 ngày đầu

Hội viên đang có gói còn hiệu lực, chưa có gói trả trước trong tương lai, được nâng sang gói dài hơn và có giá cao hơn trong 0–3 ngày kể từ ngày lập hóa đơn gói hiện tại. Giá trị gói cũ (kể cả khoản đã khấu trừ từ lần nâng trước) được trừ khỏi giá gói mới. Giá và khoản khấu trừ được chốt khi lập hóa đơn, không nhận từ trình duyệt. Khi lễ tân xác nhận khoản chênh lệch, gói mới bắt đầu đủ số tháng từ ngày xác nhận; gói cũ kết thúc và lưu hạn cũ trong lịch sử. Không cộng thêm ngày còn lại của gói cũ. Ngoài điều kiện trên, đăng ký là gia hạn theo cơ chế cũ. Doanh thu chỉ cộng tiền thực thu.

### Thông báo hội viên

Chuông trên thanh tài khoản hiển thị 8 thông báo mới nhất và tổng số chưa đọc; trang thông báo hiển thị 100 mục mới nhất. Bấm thông báo để đánh dấu đã đọc và mở trang liên quan; có nút đánh dấu tất cả đã đọc. Dữ liệu lưu trong SQLite và cập nhật khi tải trang. Tạo thông báo khi xác nhận thanh toán gói (admin/lễ tân), HLV nhận hội viên hoặc thêm lịch tập, đổi email, đổi mật khẩu hoặc nhân viên đặt lại mật khẩu. Không lưu mật khẩu trong thông báo. Chỉ hội viên sở hữu mới xem/đánh dấu được thông báo của mình.
