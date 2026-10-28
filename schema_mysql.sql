-- MySQL 8.0.16+ - run inside a dedicated gym_demo database.
CREATE TABLE IF NOT EXISTS users (
 id INT PRIMARY KEY AUTO_INCREMENT,
 username VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin UNIQUE,
 password VARCHAR(255), role VARCHAR(20),
 auth_version INT NOT NULL DEFAULT 0,
 full_name VARCHAR(120) NOT NULL DEFAULT '', active TINYINT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS packages (
 id INT PRIMARY KEY AUTO_INCREMENT, months INT UNIQUE, price INT CHECK(price>0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS members (
 id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(120), gender VARCHAR(10), birth INT,
 phone VARCHAR(30), email VARCHAR(254), registered DATE, source VARCHAR(40),
 trainer INT, user_id INT UNIQUE, deleted_at DATETIME(6),
 FOREIGN KEY(trainer) REFERENCES users(id), FOREIGN KEY(user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS invoices (
 id INT PRIMARY KEY AUTO_INCREMENT, member INT, months INT, amount INT,
 created DATE, paid_at DATE, starts DATE, expires DATE,
 upgrade_from INT, credit_amount INT NOT NULL DEFAULT 0, original_expires DATE,
 FOREIGN KEY(member) REFERENCES members(id), FOREIGN KEY(upgrade_from) REFERENCES invoices(id),
 INDEX invoices_member(member)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS exercises (
 id INT PRIMARY KEY AUTO_INCREMENT,
 name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin UNIQUE,
 active TINYINT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS plans (
 id INT PRIMARY KEY AUTO_INCREMENT, member INT, exercise INT, sets INT, reps INT,
 days VARCHAR(20), active TINYINT NOT NULL DEFAULT 1,
 FOREIGN KEY(member) REFERENCES members(id), FOREIGN KEY(exercise) REFERENCES exercises(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS settings (
 id INT PRIMARY KEY CHECK(id=1), max_days INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS trainer_requests (
 id INT PRIMARY KEY AUTO_INCREMENT, member INT NOT NULL, trainer INT NOT NULL,
 status VARCHAR(12) NOT NULL CHECK(status IN ('pending','accepted','rejected','cancelled')),
 created DATETIME(6) NOT NULL, responded DATETIME(6),
 pending_member INT GENERATED ALWAYS AS (CASE WHEN status='pending' THEN member ELSE NULL END) STORED,
 UNIQUE KEY one_pending_trainer_request(pending_member),
 FOREIGN KEY(member) REFERENCES members(id), FOREIGN KEY(trainer) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS notifications (
 id INT PRIMARY KEY AUTO_INCREMENT, member INT NOT NULL, message TEXT NOT NULL,
 link VARCHAR(255) NOT NULL, created DATETIME(6) NOT NULL, read_at DATETIME(6),
 FOREIGN KEY(member) REFERENCES members(id), INDEX notifications_member(member,id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS staff_notifications (
 id INT PRIMARY KEY AUTO_INCREMENT, user_id INT NOT NULL, message TEXT NOT NULL,
 link VARCHAR(255) NOT NULL, created DATETIME(6) NOT NULL, read_at DATETIME(6),
 FOREIGN KEY(user_id) REFERENCES users(id), INDEX staff_notifications_user(user_id,id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS app_migrations (name VARCHAR(100) PRIMARY KEY) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT IGNORE INTO settings(id,max_days) VALUES(1,6);
