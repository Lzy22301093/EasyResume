"""Auth 测试 — JWT + 用户认证。"""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.models.orm import User
from app.services.auth_service import AuthService


@pytest.fixture(autouse=True)
def jwt_secret():
    """JWT 密钥从环境注入：为测试提供固定密钥，避免依赖 .env。"""
    import app.services.auth_service as auth_module
    original = auth_module.SECRET_KEY
    auth_module.SECRET_KEY = "test-secret-key-for-pytest-0123456789"
    yield
    auth_module.SECRET_KEY = original


@pytest.fixture
def db_engine():
    """创建 SQLite 内存数据库引擎。"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_factory(db_engine):
    """创建数据库会话工厂。"""
    TestSession = sessionmaker(bind=db_engine)
    return TestSession


@pytest.fixture
def auth_service(db_factory):
    """创建 AuthService 实例。"""
    return AuthService(db_factory=db_factory)


# === 密码测试 ===


class TestPassword:
    def test_hash_password(self, auth_service: AuthService):
        """密码哈希。"""
        hashed = auth_service.hash_password("password123")
        assert hashed != "password123"
        assert auth_service.verify_password("password123", hashed) is True

    def test_verify_wrong_password(self, auth_service: AuthService):
        """错误密码验证失败。"""
        hashed = auth_service.hash_password("password123")
        assert auth_service.verify_password("wrong", hashed) is False


# === JWT 测试 ===


class TestJWT:
    def test_create_and_decode_token(self, auth_service: AuthService):
        """创建和解码 token。"""
        token = auth_service.create_access_token({"sub": "1", "username": "test"})
        payload = auth_service.decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "test"

    def test_decode_invalid_token(self, auth_service: AuthService):
        """无效 token 返回 None。"""
        payload = auth_service.decode_token("invalid-token")
        assert payload is None


# === 用户注册测试 ===


class TestRegister:
    def test_register_success(self, auth_service: AuthService):
        """注册成功。"""
        user = auth_service.register("testuser", "test@example.com", "password123")
        assert user is not None
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"

    def test_register_duplicate_username(self, auth_service: AuthService):
        """重复用户名注册失败。"""
        auth_service.register("testuser", "test1@example.com", "password123")
        result = auth_service.register("testuser", "test2@example.com", "password456")
        assert result is None

    def test_register_duplicate_email(self, auth_service: AuthService):
        """重复邮箱注册失败。"""
        auth_service.register("user1", "test@example.com", "password123")
        result = auth_service.register("user2", "test@example.com", "password456")
        assert result is None


# === 用户登录测试 ===


class TestLogin:
    def test_login_success(self, auth_service: AuthService):
        """登录成功。"""
        auth_service.register("testuser", "test@example.com", "password123")
        result = auth_service.login("testuser", "password123")
        assert result is not None
        assert "token" in result
        assert result["user"]["username"] == "testuser"

    def test_login_wrong_password(self, auth_service: AuthService):
        """密码错误登录失败。"""
        auth_service.register("testuser", "test@example.com", "password123")
        result = auth_service.login("testuser", "wrong")
        assert result is None

    def test_login_nonexistent_user(self, auth_service: AuthService):
        """不存在的用户登录失败。"""
        result = auth_service.login("nobody", "password123")
        assert result is None


# === 用户查询测试 ===


class TestGetUser:
    def test_get_by_id(self, auth_service: AuthService):
        """通过 ID 获取用户。"""
        auth_service.register("testuser", "test@example.com", "password123")
        user = auth_service.get_user_by_id(1)
        assert user is not None
        assert user["username"] == "testuser"

    def test_get_by_username(self, auth_service: AuthService):
        """通过用户名获取用户。"""
        auth_service.register("testuser", "test@example.com", "password123")
        user = auth_service.get_user_by_username("testuser")
        assert user is not None
        assert user["email"] == "test@example.com"

    def test_get_nonexistent(self, auth_service: AuthService):
        """获取不存在的用户返回 None。"""
        assert auth_service.get_user_by_id(999) is None
        assert auth_service.get_user_by_username("nobody") is None


def test_legacy_pbkdf2_password_still_verifies_and_upgrades(auth_service: AuthService):
    """历史 PBKDF2 密码可登录，并在成功后透明升级为 bcrypt。"""
    import os

    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", b"password123", salt, 100000)
    legacy = salt.hex() + ":" + key.hex()
    user = auth_service.register("legacy", "legacy@example.com", "password123")
    db = auth_service._get_db()
    try:
        row = db.query(User).filter(User.id == user["id"]).first()
        row.hashed_password = legacy
        db.commit()
    finally:
        db.close()

    result = auth_service.login("legacy", "password123")
    assert result is not None
    db = auth_service._get_db()
    try:
        row = db.query(User).filter(User.id == user["id"]).first()
        assert row.hashed_password.startswith(("$2a$", "$2b$", "$2y$"))
    finally:
        db.close()


def test_register_returns_none_on_unique_key_race(auth_service: AuthService, monkeypatch):
    """并发注册触发唯一键冲突时返回“已存在”，不向接口抛 500。"""
    from sqlalchemy.exc import IntegrityError

    def conflict():
        raise IntegrityError("insert user", {}, Exception("duplicate"))

    # 使用独立会话模拟：让预检查通过，但最终插入提交冲突
    original_factory = auth_service._db_factory

    class ConflictSession:
        def __init__(self, session):
            self.session = session

        def __getattr__(self, name):
            return getattr(self.session, name)

        def commit(self):
            raise IntegrityError("insert user", {}, Exception("duplicate"))

    def factory():
        return ConflictSession(original_factory())

    auth_service._db_factory = factory
    assert auth_service.register("race", "race@example.com", "password123") is None


def test_register_request_rejects_invalid_email():
    from app.api.auth import RegisterRequest

    with pytest.raises(ValidationError):
        RegisterRequest(username="testuser", email="not-an-email", password="password123")
