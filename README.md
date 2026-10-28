# Quản lý phòng tập Gym — Flask + MySQL

Ứng dụng mặc định sử dụng **MySQL 8.0.16 trở lên**, InnoDB, utf8mb4, khóa ngoại và giao dịch. SQLite chỉ còn để kiểm thử hồi quy và đọc dữ liệu cũ khi chuyển sang MySQL; không phải cơ sở dữ liệu mặc định của web.

## Cài đặt lần đầu trên Windows / PyCharm

1. Bật dịch vụ MySQL Server. MySQL Workbench chỉ là công cụ quản lý, vẫn cần MySQL Server đang chạy.
2. Mở terminal tại thư mục dự án và cài thư viện bằng Python của môi trường `.venv`:

```bash
python -m pip install -r requirements.txt
```

3. Trong MySQL Workbench hoặc MySQL console, chạy bằng tài khoản quản trị. Thay `CHANGE_ME_DATABASE_PASSWORD` bằng mật khẩu riêng, dùng cùng giá trị trong `.env`:

```sql
CREATE DATABASE IF NOT EXISTS gym_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'gym_app'@'127.0.0.1' IDENTIFIED BY 'CHANGE_ME_DATABASE_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON gym_demo.* TO 'gym_app'@'127.0.0.1';
```

4. Sao chép `.env.example` thành **`.env`** ngay cạnh `index.py`. Trong Git Bash:

```bash
cp .env.example .env
```

Điền MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD và các giá trị SMTP thật vào `.env`. Không chạy lại lệnh sao chép nếu đã có `.env` chứa cấu hình của bạn. Mật khẩu chứa ký tự `#` hoặc khoảng trắng nên đặt trong dấu nháy kép.

Tạo SECRET_KEY riêng bằng lệnh sau rồi điền vào `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Không đưa `.env` lên GitHub.** `.gitignore` đã chặn file này. Biến môi trường đang có trong PyCharm được ưu tiên hơn `.env`; nếu trước đây đã nhập SMTP trong Run Configuration, hãy xóa các biến SMTP cũ ở đó để chuyển sang dùng file.

5. Nếu cần giữ dữ liệu SQLite cũ, làm bước chuyển dữ liệu bên dưới **trước lần Run đầu tiên với MySQL**.
6. Run Flask trong PyCharm hoặc:

```bash
python -m flask --app index run
```

Khi khởi động, ứng dụng tạo các bảng còn thiếu từ `schema_mysql.sql` và tài khoản mặc định trên database đã tạo. Không tự đổi cấu trúc database của một ứng dụng khác; nên dùng riêng database `gym_demo`.

## Giữ tài khoản và dữ liệu SQLite cũ

Sao lưu `gym.db` trước. Công cụ chỉ đọc nguồn, không xóa hay sửa file SQLite. Database MySQL đích phải trống, chưa được web tạo dữ liệu mặc định:

```bash
python migrate_sqlite_to_mysql.py --source gym.db
```

Nếu đích đã có dữ liệu, công cụ sẽ dừng; hãy dùng một database mới và cập nhật MYSQL_DATABASE trong `.env`. Không xóa dữ liệu MySQL đang dùng để chạy lại công cụ.

Công cụ giữ ID hội viên/HLV, mật khẩu đã băm, liên kết tài khoản, hóa đơn, lịch tập và thông báo. Thao tác chép dữ liệu là một giao dịch: lỗi giữa chừng sẽ rollback các bản ghi đã chép. Việc tạo bảng của MySQL là DDL, có thể vẫn để lại bảng trống khi thất bại. Sau khi chép xong, chạy web bình thường. Không mở đồng thời bản SQLite và MySQL để cập nhật cùng một bộ dữ liệu.

## SMTP

`.env` chứa:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=your-sender@gmail.com
SMTP_USER=your-sender@gmail.com
SMTP_PASSWORD=YOUR_APP_PASSWORD
```

Dùng Gmail và mật khẩu ứng dụng của chính Gmail gửi thư. Không dùng mật khẩu Gmail thông thường. Email hợp lệ bắt buộc khi đăng ký hội viên trực tuyến hoặc tại quầy. Web gọi SMTP sau khi tạo hội viên thành công và khi chọn gói tập. Nếu gửi thư lỗi, đăng ký vẫn được lưu và giao diện báo rõ; xem `SMTP failed` trong Run để chẩn đoán. Thay `.env` xong phải Stop và Run lại.

## Tài khoản và phân quyền

- Database mới có `admin` và `letan`, mật khẩu mặc định `Gym@12345`. Có thể đặt DEMO_PASSWORD trước lần khởi tạo đầu tiên. Đổi mật khẩu trước khi dùng thật.
- Hội viên đăng ký tại `/signup`, đăng nhập bằng số điện thoại và mật khẩu. Email bắt buộc, không dùng để đăng nhập.
- Admin/lễ tân đăng ký, xóa hội viên, xác nhận thanh toán, đặt lại mật khẩu hội viên và tạo/xóa tài khoản HLV.
- Admin chỉ sửa giá gói trong Bảng giá (`/settings`). Hóa đơn đã lập giữ nguyên giá tại thời điểm tạo.
- HLV nhận yêu cầu trước khi lập lịch, chỉ thấy danh sách hội viên đã nhận của mình. HLV quản lý danh mục bài tập chung tại `/exercises`; xóa chỉ ẩn khỏi lựa chọn mới, giữ lịch sử.
- Trang hội viên: Trang chủ (gói, hạn, số ngày còn lại, lịch tập), Thông tin (email, mật khẩu, HLV), Đăng ký gói tập (gói và hóa đơn).
- Mã hiển thị: HV_01 / HLV_03; ID từ 100 trở lên không bị cắt. Ngày hiển thị dd/mm/yyyy, thông báo có thêm HH:mm.
- Chuông lưu thông báo riêng cho hội viên và nhân viên; “Đọc thông báo” đánh dấu đã đọc ngay tại trang đang xem.

## Gói tập, thu tiền và thống kê

Giá ban đầu: 1 tháng 500.000đ, 3 tháng 1.200.000đ, 6 tháng 2.000.000đ, 12 tháng 3.500.000đ. Hội viên chọn gói tạo hóa đơn chờ, lễ tân/admin xác nhận thanh toán mới kích hoạt. Gia hạn thường nối từ hạn cuối đã thanh toán. Hội viên không được chọn gói thấp hơn gói còn hạn hoặc đã đăng ký.

Nâng lên gói dài hơn, giá cao hơn trong 0–3 ngày kể từ ngày đăng ký gói đang dùng, chưa có gói trả trước tương lai: trừ toàn bộ giá trị gói cũ, thu chênh lệch. Khi xác nhận, gói mới bắt đầu từ ngày thu tiền, đủ thời hạn mới và thay thời hạn cũ. Hạn cũ được lưu để tra cứu; doanh thu chỉ cộng tiền thực thu.

Admin/lễ tân xem hội viên đăng ký theo tháng, doanh thu theo tháng và số hội viên còn hạn. Mỗi hội viên còn hạn chỉ tính một lần; ngày hết hạn là mốc kết thúc không bao gồm ngày đó. HLV xem lịch đã xếp, không xem doanh thu. Chart.js cần kết nối CDN; khi không tải được vẫn có bảng số liệu chi tiết.

## Kiểm thử

Hồi quy SQLite, không cần MySQL Server:

```bash
python -m unittest discover -s tests -v
```

Kiểm tra các luồng trên **MySQL thật**, mỗi bài tạo database `gym_test_*` riêng rồi xóa. Chỉ dùng tài khoản kiểm thử có quyền CREATE/DROP các database này; tuyệt đối không dùng database đang vận hành. Thiết lập MYSQL_TEST_HOST, MYSQL_TEST_PORT, MYSQL_TEST_USER, MYSQL_TEST_PASSWORD, rồi chạy:

```bash
python tests/run_mysql.py
```

Bài kiểm tra chuyển cấu trúc SQLite cũ được chạy trong bộ SQLite, bỏ qua trong bộ MySQL. Luồng gửi thư được giả lập; kiểm thử tự động không gửi email thật.
