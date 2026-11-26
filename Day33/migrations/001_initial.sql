-- Initial schema for a new, empty MySQL 8 database. Application timestamps are UTC.
CREATE TABLE menu_items (
  id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, title VARCHAR(120) NOT NULL,
  category VARCHAR(80) NOT NULL, vegetarian BOOL NOT NULL, price NUMERIC(12,2) NOT NULL,
  capacity INTEGER NOT NULL, active BOOL NOT NULL, created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL, CHECK (price > 0), CHECK (capacity >= 0)
);
CREATE INDEX ix_menu_items_category ON menu_items (category);
CREATE TABLE users (
  id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL, role VARCHAR(16) NOT NULL, created_at DATETIME NOT NULL
);
CREATE TABLE chat_sessions (
  id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, user_id INTEGER NOT NULL,
  title VARCHAR(120) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id)
);
CREATE INDEX ix_chat_sessions_user_id ON chat_sessions (user_id);
CREATE TABLE documents (
  id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, filename VARCHAR(255) NOT NULL,
  sha256 VARCHAR(64) NOT NULL, version INTEGER NOT NULL, status VARCHAR(20) NOT NULL,
  uploaded_by INTEGER NOT NULL, created_at DATETIME NOT NULL, FOREIGN KEY (uploaded_by) REFERENCES users (id)
);
CREATE INDEX ix_documents_filename ON documents (filename);
CREATE TABLE orders (
  id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, user_id INTEGER NOT NULL, status VARCHAR(24) NOT NULL,
  total NUMERIC(12,2) NOT NULL, idempotency_key VARCHAR(128) NOT NULL, request_hash VARCHAR(64) NOT NULL,
  cancel_key VARCHAR(128), created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  UNIQUE (user_id, idempotency_key), FOREIGN KEY (user_id) REFERENCES users (id)
);
CREATE INDEX ix_orders_status ON orders (status);
CREATE INDEX ix_orders_user_id ON orders (user_id);
CREATE TABLE chat_messages (
  id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, session_id INTEGER NOT NULL, seq_no INTEGER NOT NULL,
  role VARCHAR(16) NOT NULL, content LONGTEXT NOT NULL, metadata JSON NOT NULL, created_at DATETIME NOT NULL,
  UNIQUE (session_id, seq_no), FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
);
CREATE INDEX ix_chat_messages_session_id ON chat_messages (session_id);
CREATE INDEX ix_chat_session_seq ON chat_messages (session_id, seq_no);
CREATE TABLE order_lines (
  id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, order_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL, unit_price NUMERIC(12,2) NOT NULL, CHECK (quantity > 0), CHECK (unit_price > 0),
  FOREIGN KEY (order_id) REFERENCES orders (id), FOREIGN KEY (item_id) REFERENCES menu_items (id)
);
CREATE INDEX ix_order_lines_order_id ON order_lines (order_id);
CREATE TABLE pending_actions (
  id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, session_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
  action VARCHAR(32) NOT NULL, payload JSON NOT NULL, expires_at DATETIME NOT NULL, status VARCHAR(20) NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL UNIQUE, result JSON, created_at DATETIME NOT NULL,
  FOREIGN KEY (session_id) REFERENCES chat_sessions (id), FOREIGN KEY (user_id) REFERENCES users (id)
);
CREATE INDEX ix_pending_actions_session_id ON pending_actions (session_id);
CREATE INDEX ix_pending_actions_user_id ON pending_actions (user_id);
CREATE TABLE tool_runs (
  id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, message_id INTEGER NOT NULL, tool_name VARCHAR(80) NOT NULL,
  args JSON NOT NULL, result JSON NOT NULL, status VARCHAR(16) NOT NULL, created_at DATETIME NOT NULL,
  FOREIGN KEY (message_id) REFERENCES chat_messages (id)
);
CREATE INDEX ix_tool_runs_message_id ON tool_runs (message_id);
