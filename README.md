# Quản lý phòng tập Gym — bản thử nghiệm Flask

## Chạy trong PyCharm (Python 3.10 trở lên)
1. Giải nén rồi mở thư mục gym_demo trong PyCharm.
2. Chọn Python interpreter/virtual environment cho dự án.
3. Mở Terminal: `python -m pip install -r requirements.txt`
4. Nhấp phải index.py > Run, hoặc chạy `python index.py`.
5. Mở http://127.0.0.1:5000. Không mở index.html trực tiếp.

SQLite gym.db tự tạo khi chạy index.py lần đầu. Khởi động lại không mất dữ liệu.

## Tài khoản mẫu
Mật khẩu chung ban đầu: Gym@12345
- admin: toàn quyền
- letan: đăng ký tại quầy, xem hội viên, gán HLV
- hlv: tạo/xóa lịch cho hội viên được phân công
- thungan: xem hóa đơn và xác nhận đã thu tiền
Đăng ký tài khoản trực tuyến: http://127.0.0.1:5000/signup.
Có thể đặt biến môi trường DEMO_PASSWORD trước lần chạy đầu để đổi mật khẩu khởi tạo.

## Kịch bản chạy thử
1. Tạo tài khoản tại /signup, đăng nhập rồi chọn gói tại /account.
2. Đăng nhập admin hoặc letan, vào Hội viên, gán HLV hlv.
3. Đăng nhập admin hoặc thungan, vào Thanh toán, xác nhận đã thu tiền.
4. Đăng nhập hlv, tạo Squat, 3 hiệp, 15 lần, Thứ 2/4/6.
5. Xem Tổng quan: hội viên còn hạn, đăng ký và doanh thu theo tháng trong năm hiện tại.
6. Admin vào Quy định để đổi giá, thêm/sửa/xóa bài tập và giới hạn ngày tập.

## Quy ước
- Hóa đơn lập khi đăng ký, lưu giá tại thời điểm lập. Đổi giá không sửa hóa đơn cũ.
- Chỉ hóa đơn đã thu tiền mới tính doanh thu; tháng tính theo ngày thu tiền.
- Gói tập bắt đầu khi thu tiền; hết hạn theo tháng lịch, ngày hết hạn không còn hiệu lực.
- Tổng số ngày KHÁC NHAU trong mọi bài tập của một hội viên không vượt giới hạn.
- Giảm giới hạn bị chặn nếu lịch hiện tại vượt mức mới: sửa/xóa lịch trước.
- Xóa danh mục là ẩn bài tập, giữ lịch tập đã tạo.
- Bản thử nghiệm chưa có hoàn tiền, xuất hóa đơn PDF hoặc quản lý tài khoản nhân viên. Mỗi lần đăng ký mới tạo một hội viên mới. Lịch sử thanh toán thể hiện trong bảng hóa đơn theo mã hội viên.

## Email SMTP (tùy chọn)
Trong PyCharm: Run > Edit Configurations > Environment variables, thêm:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=email-cua-ban@gmail.com
SMTP_USER=email-cua-ban@gmail.com
SMTP_PASSWORD=mat-khau-ung-dung
SECRET_KEY=chuoi-ngau-nhien-dai-cua-ban

Dùng mật khẩu ứng dụng của nhà cung cấp email. Không ghi mật khẩu vào code hoặc đẩy lên GitHub.
Khi không cấu hình SMTP hoặc gửi lỗi: hội viên vẫn được lưu, giao diện báo rõ chưa gửi.
Email chỉ gửi sau đăng ký, không gửi lúc khởi động. Chỉ dùng địa chỉ bạn có quyền thử nghiệm.
Biểu đồ Chart.js tải từ CDN nên cần Internet; bảng số liệu luôn có để đối chiếu.

## Giới hạn triển khai
Đây là bản chạy thử trên localhost, không phải hệ thống sẵn sàng triển khai công khai.
Có phân quyền phía server, băm mật khẩu, CSRF và SQL tham số hóa.
Trước triển khai thật cần quản lý tài khoản/mật khẩu, giới hạn đăng nhập, HTTPS, sao lưu,
xử lý email nền và kiểm tra dữ liệu email/điện thoại đầy đủ hơn.
Không đưa gym.db chứa thông tin hội viên lên GitHub.


## Tài khoản hội viên (luồng mới)
1. Mở /signup: nhập hồ sơ, email, mật khẩu và xác nhận mật khẩu.
2. Tạo tài khoản chỉ tạo hồ sơ, chưa tạo hóa đơn hay kích hoạt gói tập.
3. Đăng nhập bằng email ở /login, chọn gói trên /account.
4. Thu ngân xác nhận thanh toán; hội viên xem hạn gói, HLV, lịch tập và hóa đơn riêng.
5. Chỉ được có một hóa đơn chờ thanh toán; có thể mua tiếp/gia hạn sau khi hóa đơn được thu.

/register chỉ dành cho lễ tân/admin đăng ký tại quầy; người chưa đăng nhập phải tạo tài khoản trước.
Dữ liệu cũ được giữ khi chạy lại index.py: tự thêm cột liên kết tài khoản và chỉ mục duy nhất.
Hồ sơ cũ không tự gắn tài khoản theo email (email chưa được xác minh). Nếu email đã có hồ sơ,
đăng ký tài khoản bị chặn và yêu cầu liên hệ lễ tân. Luồng kích hoạt tài khoản cho hồ sơ cũ chưa có giao diện.
Không xóa gym.db khi cập nhật. Sao lưu gym.db trước khi nâng cấp.
Thống kê đăng ký hội viên tính theo ngày tạo hồ sơ tài khoản; doanh thu chỉ tính sau khi thu tiền.
Email SMTP được gửi khi chọn gói thành công, không gửi khi mới tạo tài khoản.
Chưa có xác minh email, quên mật khẩu hoặc giới hạn thử đăng nhập; chỉ dùng localhost demo.

Chạy kiểm tra: `python -m unittest discover -s tests -v`.
