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
- admin: quản lý, báo cáo, quy định, tạo tài khoản HLV; không xếp lịch tập
- letan: quản lý hội viên, gửi yêu cầu HLV, thu tiền và đặt lại mật khẩu hội viên
- HLV: do admin hoặc lễ tân tạo tại Quản lý HLV, nhận yêu cầu và lập/xóa lịch được phân công
Đăng ký tài khoản trực tuyến: http://127.0.0.1:5000/signup.
Có thể đặt biến môi trường DEMO_PASSWORD trước lần chạy đầu để đổi mật khẩu khởi tạo.

## Kịch bản chạy thử
1. Tạo tài khoản tại /signup, đăng nhập rồi chọn gói tại /account.
2. Admin/lễ tân vào Quản lý HLV để tạo tài khoản; hội viên chọn HLV đó tại trang cá nhân và gửi yêu cầu.
3. Đăng nhập admin hoặc letan, vào Thanh toán, xác nhận đã thu tiền.
4. Đăng nhập tài khoản HLV vừa tạo, vào Yêu cầu HLV và xác nhận, sau đó tạo Squat, 3 hiệp, 15 lần, Thứ 2/4/6.
5. Xem Tổng quan: hội viên còn hạn, đăng ký và doanh thu theo tháng trong năm hiện tại.
6. Admin vào Quy định để đổi giá, thêm/sửa/xóa bài tập và giới hạn ngày tập.

## Quy ước
- Hóa đơn lập khi đăng ký, lưu giá tại thời điểm lập. Đổi giá không sửa hóa đơn cũ.
- Chỉ hóa đơn đã thu tiền mới tính doanh thu; tháng tính theo ngày thu tiền.
- Gói tập bắt đầu khi thu tiền; hết hạn theo tháng lịch, ngày hết hạn không còn hiệu lực.
- Tổng số ngày KHÁC NHAU trong mọi bài tập của một hội viên không vượt giới hạn.
- Giảm giới hạn bị chặn nếu lịch hiện tại vượt mức mới: sửa/xóa lịch trước.
- Xóa danh mục là ẩn bài tập, giữ lịch tập đã tạo.
- Bản thử nghiệm chưa có hoàn tiền, xuất hóa đơn PDF hoặc quản lý đầy đủ tài khoản nhân viên ngoài việc tạo HLV. Mỗi lần đăng ký mới tạo một hội viên mới. Lịch sử thanh toán thể hiện trong bảng hóa đơn theo mã hội viên.

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
1. Mở /signup: nhập hồ sơ, số điện thoại, mật khẩu và xác nhận mật khẩu.
2. Tạo tài khoản chỉ tạo hồ sơ, chưa tạo hóa đơn hay kích hoạt gói tập.
3. Đăng nhập bằng số điện thoại ở /login, chọn gói trên /account.
4. Lễ tân xác nhận thanh toán; hội viên xem hạn gói, HLV, lịch tập và hóa đơn riêng.
5. Chỉ được có một hóa đơn chờ thanh toán; có thể mua tiếp/gia hạn sau khi hóa đơn được thu.

/register chỉ dành cho lễ tân/admin đăng ký tại quầy; người chưa đăng nhập phải tạo tài khoản trước.
Dữ liệu cũ được giữ khi chạy lại index.py: tự thêm cột liên kết tài khoản và chỉ mục duy nhất.
Hồ sơ cũ không tự gắn tài khoản mới theo số điện thoại. Nếu số điện thoại đã có hồ sơ,
đăng ký tài khoản bị chặn và yêu cầu liên hệ lễ tân. Luồng kích hoạt tài khoản cho hồ sơ cũ chưa có giao diện.
Không xóa gym.db khi cập nhật. Sao lưu gym.db trước khi nâng cấp.
Thống kê đăng ký hội viên tính theo ngày tạo hồ sơ tài khoản; doanh thu chỉ tính sau khi thu tiền.
Email SMTP được gửi khi chọn gói thành công, không gửi khi mới tạo tài khoản.
Chưa có xác minh email, tự khôi phục mật khẩu hoặc giới hạn thử đăng nhập; chỉ dùng localhost demo.

Chạy kiểm tra: `python -m unittest discover -s tests -v`.

## Đăng nhập bằng số điện thoại
Hội viên dùng số điện thoại + mật khẩu, nhân viên vẫn dùng tài khoản cũ.
Email tùy chọn khi đăng ký và có thể thêm/sửa/bỏ sau đó ở Trang cá nhân > Lưu email.
Không có email thì bỏ qua gửi SMTP; đăng ký gói và thanh toán vẫn hoạt động.
Tài khoản hội viên cũ dùng số điện thoại trong hồ sơ và mật khẩu cũ; không đổi ID, hóa đơn hay lịch tập.
Chấp nhận số 9–15 chữ số, bỏ khoảng trắng/dấu chấm/gạch ngang/ngoặc, đổi +84 thành 0.
Nếu hồ sơ cũ trùng số điện thoại, chặn đăng nhập thay vì đoán tài khoản; cần lễ tân hỗ trợ.
Email không còn là định danh đăng nhập. Chưa có OTP xác minh số điện thoại.

## Đăng ký lại số điện thoại sau khi xóa
Chỉ hồ sơ chưa xóa giữ số điện thoại. Sau khi xóa, số đó được đăng ký tài khoản mới.
Tài khoản mới có ID, mật khẩu và hồ sơ riêng; không xem được hóa đơn/lịch tập cũ.
Lịch sử đã thu vẫn giữ ở hồ sơ cũ; tài khoản và phiên đăng nhập cũ vẫn bị khóa.
Nếu số thuộc hồ sơ tại quầy chưa có tài khoản và chưa xóa, cần lễ tân hỗ trợ, không tự chiếm hồ sơ.

## Đổi và đặt lại mật khẩu
- Hội viên: Trang cá nhân > Đổi mật khẩu. Nhập mật khẩu hiện tại, mật khẩu mới và nhập lại.
- Quản trị viên hoặc lễ tân: Hội viên > Đặt lại mật khẩu (chỉ hồ sơ đang hoạt động có tài khoản).
  Nhập mật khẩu tài khoản đang thao tác để xác nhận, sau đó mật khẩu mới cho hội viên và nhập lại.
- Mật khẩu mới có 8–128 ký tự, chỉ lưu dạng băm; không hiển thị hoặc gửi mật khẩu qua email.
- Đổi/đặt lại mật khẩu tăng phiên bản xác thực; mọi phiên cũ bị chặn ở lần truy cập tiếp theo.
  Hội viên tự đổi sẽ được đưa về đăng nhập ngay; quản trị viên giữ phiên hiện tại.
- Hồ sơ tại quầy chưa có tài khoản hoặc hồ sơ đã xóa không được đặt lại mật khẩu.
- Database tự thêm auth_version khi khởi động, giữ các tài khoản và dữ liệu cũ.

## Gộp thu ngân vào lễ tân và xếp lịch cho HLV
Chỉ còn vai trò admin, reception (lễ tân kiêm thu ngân), trainer và member.
Không tạo tài khoản thungan cho database mới; tài khoản cashier cũ được chuyển sang reception, giữ mật khẩu.
Lễ tân có Thanh toán, Xóa hội viên và Đặt lại mật khẩu (xác nhận bằng mật khẩu của chính lễ tân).
HLV có trang Hội viên chỉ đọc và mục Yêu cầu HLV để xác nhận hoặc từ chối.

## Hội viên chọn HLV và HLV xác nhận
1. Hội viên đăng nhập > Trang cá nhân > Đăng ký huấn luyện viên > chọn HLV > Gửi yêu cầu.
2. HLV đăng nhập > Yêu cầu HLV > Xác nhận làm HLV hoặc Từ chối.
3. Chỉ sau khi xác nhận, HLV mới được tạo/xóa lịch cho hội viên đó.
- Hội viên có thể hủy yêu cầu đang chờ để chọn HLV khác. Mỗi người chỉ có một yêu cầu chờ.
- Khi đã được nhận: Hủy đăng ký HLV > xác nhận, sau đó chọn HLV khác và chờ xác nhận mới.
- Lễ tân/admin có thể gửi yêu cầu hỗ trợ tại quầy, không thể bỏ qua xác nhận của HLV.
- Không còn tự phân công khi tạo lịch. Chỉ HLV đã xác nhận được lập lịch; admin/lễ tân không xếp lịch.
- Chỉ HLV được chọn mới xử lý yêu cầu đó. Yêu cầu đã xử lý/hủy không được xử lý lại.
- Xóa hội viên hủy yêu cầu chờ; giữ lịch sử đã có.
- Nâng cấp lần đầu: phân công cũ chuyển thành yêu cầu chờ HLV xác nhận; giữ lịch tập/hóa đơn cũ.
  Chạy lại không tạo trùng hay đặt lại yêu cầu đã được chấp nhận.

## Hủy đăng ký HLV đã được nhận
Trang cá nhân > Hủy đăng ký HLV > Xác nhận hủy. Yêu cầu chuyển sang Đã hủy, bỏ liên kết HLV.
Lịch tập hiện tại được đánh dấu ngừng hoạt động, giữ dữ liệu cũ nhưng không hiển thị như lịch hiện tại
và không tính vào giới hạn ngày tập. HLV cũ không lập/xóa lịch của hội viên được nữa.
Gói Gym, thời hạn, hóa đơn và số tiền đã thanh toán không bị thay đổi; không có phí HLV riêng ở bản demo.
Hội viên có thể gửi yêu cầu chọn HLV mới; cần xác nhận mới trước khi lập lịch mới.
Đổi mật khẩu được đặt bên phải Lưu email trong phần thông tin cá nhân.

## Danh sách hội viên của HLV
HLV chỉ thấy người có liên kết hiện tại với chính HLV đó và có yêu cầu Đã nhận.
Áp dụng cả trang Hội viên và danh sách chọn tại Lịch tập; không trả thông tin hội viên khác ra HTML.
Người chưa đăng ký, đang chờ, đã hủy, đã xóa hoặc thuộc HLV khác không xuất hiện.
Yêu cầu đang chờ vẫn hiển thị riêng ở Yêu cầu HLV. Lễ tân/admin vẫn xem danh sách chung, không lập lịch tập.

## Tạo tài khoản HLV và quyền xếp lịch
Admin hoặc lễ tân vào Quản lý HLV > nhập họ tên, tên đăng nhập, mật khẩu và nhập lại > Tạo tài khoản.
Tên đăng nhập 3–40 ký tự, bắt đầu bằng chữ không dấu, có thể chứa số và . _ -; không trùng tài khoản khác.
Mật khẩu 8–128 ký tự, chỉ lưu dạng băm và không hiển thị trong danh sách.
Vai trò luôn là trainer, người tạo không thể dùng form này để tạo admin/lễ tân.
Database mới không tự tạo hlv mặc định; tài khoản HLV cũ được giữ nguyên.
HLV vừa tạo xuất hiện trong danh sách để hội viên chọn, cần xác nhận trước khi lập lịch.
Admin/lễ tân không có nút Lịch tập hoặc Lập lịch; truy cập trực tiếp /plans và xóa lịch cũng bị chặn.

## Xóa HLV
Admin/lễ tân > Quản lý HLV > Xóa HLV > nhập mã xác nhận. Chỉ xóa tài khoản có vai trò HLV.
Tài khoản HLV bị ẩn/khóa, mọi phiên cũ bị chặn; không xóa dữ liệu lịch sử khỏi database.
Yêu cầu đang chờ/đã nhận với HLV đó chuyển thành Đã hủy, các hội viên bỏ liên kết HLV.
Lịch tập đang hoạt động của những hội viên đang thuộc HLV bị xóa được dừng, giữ lịch sử.
Gói Gym và hóa đơn không đổi; hội viên có thể chọn HLV khác. Các HLV/hội viên khác không bị ảnh hưởng.
Tên đăng nhập cũ được giải phóng để có thể tạo HLV mới; tài khoản mới có ID riêng, không nhận dữ liệu cũ.

## Trang chính của HLV
Sau đăng nhập, HLV thấy bảng Lịch đã xếp: hội viên, bài tập, số hiệp, số lần/hiệp và ngày tập.
Chỉ hiển thị lịch đang hoạt động của người đã được chính HLV đó xác nhận.
Không hiển thị hoặc truy vấn dữ liệu doanh thu/đăng ký theo tháng trên trang chính HLV.
Admin/lễ tân vẫn xem Tổng quan thống kê như trước. Trang Lịch tập vẫn dùng để thêm/xóa bài tập.
