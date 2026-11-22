from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from pydantic import field_validator
from sqlalchemy import func
from sqlmodel import Field, Session, SQLModel, create_engine, select


DATABASE_FILE = Path(__file__).resolve().with_name("food.db")
DATABASE_URL = f"sqlite:///{DATABASE_FILE.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


class RestaurantBase(SQLModel):
    """餐廳共用欄位與驗證規則。"""

    name: str = Field(min_length=1, max_length=100, description="餐廳名稱")
    category: str = Field(min_length=1, max_length=50, description="食物類型")
    price_level: int = Field(ge=1, le=3, description="價位等級（1 到 3）")
    is_open: bool = Field(default=True, description="是否營業中")

    @field_validator("name", "category")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("不可為空白")
        return cleaned_value


class Restaurant(RestaurantBase, table=True):
    """restaurants 資料表。"""

    __tablename__ = "restaurants"

    id: int | None = Field(default=None, primary_key=True)


class RestaurantCreate(RestaurantBase):
    """新增餐廳時的 request model。"""


class RestaurantRead(RestaurantBase):
    """回傳餐廳資料時的 response model。"""

    id: int


class RestaurantUpdate(SQLModel):
    """部分更新餐廳時的 request model。"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    price_level: int | None = Field(default=None, ge=1, le=3)
    is_open: bool | None = None

    @field_validator("name", "category")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("更新值不可為 null")
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("不可為空白")
        return cleaned_value

    @field_validator("price_level", "is_open")
    @classmethod
    def update_value_must_not_be_null(cls, value: int | bool | None) -> int | bool:
        if value is None:
            raise ValueError("更新值不可為 null")
        return value


def create_db_and_tables() -> None:
    """建立 SQLite 檔案及尚未存在的資料表。"""

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """每個 request 使用一個獨立的資料庫 Session。"""

    with Session(engine) as session:
        yield session


def get_restaurant_or_404(restaurant_id: int, session: Session) -> Restaurant:
    restaurant = session.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="找不到指定的餐廳")
    return restaurant


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="18" fill="#173c31"/>
<path d="M18 18v12c0 5 3 8 8 8v10c0 2 1 3 3 3s3-1 3-3V18h-4v11h-3V18h-3v11h-3V18h-1Zm23 0c-5 0-8 6-8 13 0 6 3 10 7 11v6c0 2 1 3 3 3s3-1 3-3V18h-5Z" fill="#ffb44a"/>
</svg>"""


HOME_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#173c31">
  <meta name="description" content="莫名起妙，不用再煩惱等一下要吃什麼。">
  <link rel="icon" href="/favicon.ico" type="image/svg+xml">
  <title>莫名起妙不要問我要吃啥｜今天吃什麼</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #173c31;
      --ink-deep: #0f2a22;
      --orange: #f9783d;
      --orange-dark: #dd5d26;
      --gold: #ffbc55;
      --paper: #f5f8f4;
      --card: #ffffff;
      --line: #dfe8e2;
      --muted: #62736c;
      --success: #198754;
      --danger: #c84747;
      --shadow: 0 18px 50px rgba(21, 60, 49, 0.11);
      --radius-lg: 28px;
      --radius-md: 20px;
      --radius-sm: 13px;
    }

    * { box-sizing: border-box; }

    html { scroll-behavior: smooth; }

    body {
      margin: 0;
      min-width: 320px;
      color: var(--ink-deep);
      background:
        radial-gradient(circle at 8% 8%, rgba(255, 188, 85, .13), transparent 24rem),
        var(--paper);
      font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", system-ui, sans-serif;
      font-size: 16px;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }

    button, input, select { font: inherit; }
    button, select { cursor: pointer; }
    button:focus-visible, input:focus-visible, select:focus-visible, a:focus-visible {
      outline: 3px solid rgba(249, 120, 61, .35);
      outline-offset: 2px;
    }

    .shell { width: min(1180px, calc(100% - 40px)); margin: 0 auto; }

    .site-header {
      position: sticky;
      top: 0;
      z-index: 20;
      background: rgba(245, 248, 244, .88);
      border-bottom: 1px solid rgba(223, 232, 226, .8);
      backdrop-filter: blur(16px);
    }

    .nav {
      min-height: 76px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }

    .brand {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      color: var(--ink);
      text-decoration: none;
    }

    .brand-mark {
      width: 42px;
      height: 42px;
      display: grid;
      place-items: center;
      border-radius: 14px;
      color: var(--gold);
      background: var(--ink);
      box-shadow: 0 8px 22px rgba(23, 60, 49, .2);
    }

    .brand-mark svg { width: 23px; height: 23px; }
    .brand-copy { display: grid; line-height: 1.1; }
    .brand-copy strong { font-size: clamp(.98rem, 1.4vw, 1.08rem); letter-spacing: .02em; white-space: nowrap; }
    .brand-copy small { margin-top: 5px; color: var(--muted); font-size: .72rem; letter-spacing: .16em; }

    .nav-actions { display: flex; align-items: center; gap: 12px; }

    .service-state {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: .9rem;
    }

    .service-state::before {
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #25a76d;
      box-shadow: 0 0 0 5px rgba(37, 167, 109, .12);
    }

    .button {
      min-height: 46px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 9px;
      padding: 0 20px;
      border: 0;
      border-radius: 999px;
      color: white;
      background: var(--orange);
      font-weight: 800;
      text-decoration: none;
      transition: transform .2s ease, box-shadow .2s ease, background .2s ease;
    }

    .button:hover { transform: translateY(-2px); background: var(--orange-dark); box-shadow: 0 10px 24px rgba(249, 120, 61, .25); }
    .button svg { width: 18px; height: 18px; }
    .button.secondary { color: var(--ink); background: white; border: 1px solid var(--line); }
    .button.secondary:hover { background: #f9fbfa; box-shadow: 0 10px 24px rgba(23, 60, 49, .09); }
    .button.danger { background: var(--danger); }

    .hero { padding: 42px 0 24px; }

    .hero-panel {
      position: relative;
      overflow: hidden;
      min-height: 430px;
      display: grid;
      grid-template-columns: 1.15fr .85fr;
      gap: 44px;
      align-items: center;
      padding: 58px;
      border-radius: 36px;
      color: white;
      background:
        radial-gradient(circle at 88% 8%, rgba(255, 188, 85, .28), transparent 19rem),
        linear-gradient(135deg, #173c31 0%, #0f2b23 100%);
      box-shadow: 0 28px 70px rgba(15, 42, 34, .2);
    }

    .hero-panel::after {
      content: "";
      position: absolute;
      right: -70px;
      bottom: -110px;
      width: 330px;
      height: 330px;
      border: 1px solid rgba(255,255,255,.09);
      border-radius: 50%;
      box-shadow: 0 0 0 52px rgba(255,255,255,.035), 0 0 0 104px rgba(255,255,255,.025);
      pointer-events: none;
    }

    .hero-copy, .recommend-box { position: relative; z-index: 1; }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      margin-bottom: 18px;
      color: #ffcf82;
      font-size: .88rem;
      font-weight: 800;
      letter-spacing: .12em;
    }

    .eyebrow::before { content: ""; width: 28px; height: 2px; background: currentColor; }

    h1 {
      max-width: 650px;
      margin: 0;
      font-size: clamp(2.65rem, 5vw, 4.75rem);
      line-height: 1.06;
      letter-spacing: -.045em;
    }

    .hero-copy > p { max-width: 590px; margin: 22px 0 28px; color: rgba(255,255,255,.72); font-size: 1.08rem; }

    .hero-stats { display: flex; flex-wrap: wrap; gap: 18px 34px; }
    .hero-stat { display: grid; }
    .hero-stat strong { font-size: 1.45rem; color: white; }
    .hero-stat span { color: rgba(255,255,255,.58); font-size: .84rem; }

    .recommend-box {
      padding: 26px;
      border: 1px solid rgba(255,255,255,.14);
      border-radius: 26px;
      color: var(--ink-deep);
      background: rgba(255,255,255,.96);
      box-shadow: 0 20px 55px rgba(0,0,0,.2);
    }

    .recommend-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
    .recommend-heading h2 { margin: 0; font-size: 1.35rem; }
    .dice {
      width: 43px;
      height: 43px;
      display: grid;
      place-items: center;
      border-radius: 14px;
      color: var(--orange-dark);
      background: #fff0e8;
      font-size: 1.35rem;
    }

    .field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .field { display: grid; gap: 7px; }
    .field label { color: #50635b; font-size: .88rem; font-weight: 700; }

    input, select {
      width: 100%;
      min-height: 48px;
      padding: 0 14px;
      border: 1px solid #d7e2db;
      border-radius: 12px;
      color: var(--ink-deep);
      background: white;
      transition: border-color .2s ease, box-shadow .2s ease;
    }

    select {
      padding-right: 42px;
      appearance: none;
      background-image: linear-gradient(45deg, transparent 50%, #66756f 50%), linear-gradient(135deg, #66756f 50%, transparent 50%);
      background-position: calc(100% - 18px) 20px, calc(100% - 13px) 20px;
      background-size: 5px 5px, 5px 5px;
      background-repeat: no-repeat;
    }

    input:focus, select:focus { border-color: var(--orange); box-shadow: 0 0 0 4px rgba(249, 120, 61, .11); outline: none; }
    .recommend-box .button { width: 100%; margin-top: 16px; }

    .recommend-result {
      display: none;
      margin-top: 16px;
      padding: 15px;
      border-radius: 15px;
      background: #f2f7f3;
      border: 1px solid #dbe8de;
    }

    .recommend-result.show { display: flex; align-items: center; gap: 13px; animation: rise .35s ease both; }
    .result-emoji { width: 46px; height: 46px; flex: none; display: grid; place-items: center; border-radius: 14px; background: white; font-size: 1.45rem; }
    .result-copy { min-width: 0; }
    .result-copy small { display: block; color: var(--muted); }
    .result-copy strong { display: block; overflow: hidden; font-size: 1.08rem; text-overflow: ellipsis; white-space: nowrap; }

    .content { padding: 52px 0 80px; }
    .section-head { display: flex; align-items: end; justify-content: space-between; gap: 24px; margin-bottom: 24px; }
    .section-head h2 { margin: 0; font-size: clamp(1.8rem, 3vw, 2.45rem); letter-spacing: -.035em; }
    .section-head p { margin: 7px 0 0; color: var(--muted); }
    .result-count { color: var(--muted); font-size: .92rem; white-space: nowrap; }

    .toolbar {
      display: grid;
      grid-template-columns: minmax(220px, 1.6fr) 1fr 1fr;
      gap: 12px;
      margin-bottom: 28px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(255,255,255,.72);
      box-shadow: 0 10px 28px rgba(21, 60, 49, .05);
    }

    .search-wrap { position: relative; }
    .search-wrap svg { position: absolute; left: 15px; top: 50%; width: 19px; color: #70817a; transform: translateY(-50%); pointer-events: none; }
    .search-wrap input { padding-left: 44px; }

    .restaurant-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }

    .restaurant-card {
      position: relative;
      overflow: hidden;
      min-height: 278px;
      display: flex;
      flex-direction: column;
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: var(--card);
      box-shadow: 0 10px 30px rgba(21, 60, 49, .06);
      transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
    }

    .restaurant-card:hover { transform: translateY(-5px); border-color: #cbdccf; box-shadow: var(--shadow); }
    .restaurant-card::after { content: ""; position: absolute; right: -25px; top: -30px; width: 110px; height: 110px; border-radius: 50%; background: #f4f8f5; }

    .card-top { position: relative; z-index: 1; display: flex; align-items: center; justify-content: space-between; gap: 14px; }
    .food-icon { width: 56px; height: 56px; display: grid; place-items: center; border-radius: 18px; background: #fff2e9; font-size: 1.65rem; }
    .status-pill { display: inline-flex; align-items: center; gap: 7px; padding: 6px 10px; border-radius: 999px; color: var(--success); background: #eaf8f0; font-size: .78rem; font-weight: 800; }
    .status-pill::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
    .status-pill.closed { color: #8a5d5d; background: #f8eeee; }

    .card-copy { margin-top: 22px; }
    .category { color: var(--orange-dark); font-size: .82rem; font-weight: 800; letter-spacing: .08em; }
    .card-copy h3 { margin: 5px 0 8px; overflow: hidden; font-size: 1.35rem; text-overflow: ellipsis; white-space: nowrap; }
    .price { color: var(--muted); font-size: .9rem; }
    .price strong { color: var(--ink); letter-spacing: .08em; }
    .card-actions { display: flex; gap: 8px; margin-top: auto; padding-top: 24px; }

    .text-button {
      min-height: 40px;
      padding: 0 14px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--ink);
      background: white;
      font-weight: 750;
      transition: background .2s ease, border-color .2s ease;
    }

    .text-button:hover { background: #f4f8f5; border-color: #c7d8cc; }
    .text-button.delete { margin-left: auto; color: var(--danger); border-color: transparent; }
    .text-button.delete:hover { background: #fff1f1; }

    .empty-state {
      grid-column: 1 / -1;
      padding: 70px 24px;
      border: 1px dashed #cbd9d0;
      border-radius: var(--radius-lg);
      text-align: center;
      background: rgba(255,255,255,.54);
    }

    .empty-state .empty-icon { width: 66px; height: 66px; display: grid; place-items: center; margin: 0 auto 16px; border-radius: 22px; background: #edf4ef; font-size: 1.8rem; }
    .empty-state h3 { margin: 0 0 6px; }
    .empty-state p { margin: 0; color: var(--muted); }

    .skeleton { min-height: 278px; border-radius: var(--radius-lg); background: linear-gradient(100deg, #eaf0ec 25%, #f7faf8 42%, #eaf0ec 60%); background-size: 300% 100%; animation: shimmer 1.3s infinite; }

    dialog {
      width: min(560px, calc(100% - 30px));
      max-height: calc(100vh - 36px);
      padding: 0;
      border: 0;
      border-radius: 26px;
      color: var(--ink-deep);
      background: white;
      box-shadow: 0 28px 90px rgba(15, 42, 34, .3);
    }

    dialog::backdrop { background: rgba(9, 31, 24, .62); backdrop-filter: blur(5px); }
    .dialog-body { padding: 28px; }
    .dialog-head { display: flex; align-items: start; justify-content: space-between; gap: 20px; margin-bottom: 24px; }
    .dialog-head h2 { margin: 0; font-size: 1.55rem; }
    .dialog-head p { margin: 5px 0 0; color: var(--muted); font-size: .92rem; }
    .icon-button { width: 40px; height: 40px; flex: none; display: grid; place-items: center; border: 0; border-radius: 50%; color: var(--muted); background: #f0f4f1; font-size: 1.25rem; }
    .form-stack { display: grid; gap: 17px; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

    .price-options { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; }
    .price-options input { position: absolute; opacity: 0; pointer-events: none; }
    .price-options span { min-height: 62px; display: grid; place-items: center; padding: 8px; border: 1px solid var(--line); border-radius: 13px; color: var(--muted); text-align: center; font-size: .84rem; font-weight: 700; transition: all .2s ease; }
    .price-options input:checked + span { color: var(--orange-dark); border-color: var(--orange); background: #fff4ed; box-shadow: 0 0 0 3px rgba(249, 120, 61, .1); }

    .switch-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 13px 15px; border: 1px solid var(--line); border-radius: 13px; }
    .switch-row strong { display: block; }
    .switch-row small { color: var(--muted); }
    .switch { position: relative; width: 50px; height: 29px; flex: none; }
    .switch input { position: absolute; opacity: 0; }
    .switch span { position: absolute; inset: 0; border-radius: 999px; background: #c7d2cc; transition: .2s; }
    .switch span::after { content: ""; position: absolute; width: 23px; height: 23px; left: 3px; top: 3px; border-radius: 50%; background: white; box-shadow: 0 2px 6px rgba(0,0,0,.2); transition: .2s; }
    .switch input:checked + span { background: var(--success); }
    .switch input:checked + span::after { transform: translateX(21px); }

    .dialog-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }
    .dialog-error { display: none; margin-top: 14px; padding: 10px 12px; border-radius: 10px; color: #a33434; background: #fff0f0; font-size: .9rem; }
    .dialog-error.show { display: block; }

    .delete-copy { color: var(--muted); }
    .delete-copy strong { color: var(--ink-deep); }

    .toast {
      position: fixed;
      z-index: 100;
      left: 50%;
      bottom: 28px;
      max-width: calc(100% - 30px);
      padding: 12px 18px;
      border-radius: 999px;
      color: white;
      background: var(--ink-deep);
      box-shadow: 0 14px 40px rgba(0,0,0,.22);
      font-weight: 700;
      opacity: 0;
      transform: translate(-50%, 18px);
      pointer-events: none;
      transition: opacity .25s ease, transform .25s ease;
    }

    .toast.show { opacity: 1; transform: translate(-50%, 0); }
    .toast.error { background: #a83d3d; }

    footer { padding: 26px 0 42px; border-top: 1px solid var(--line); color: var(--muted); }
    .footer-inner { display: flex; justify-content: space-between; align-items: center; gap: 20px; font-size: .9rem; }
    footer a { color: var(--ink); font-weight: 700; text-decoration: none; }
    footer a:hover { color: var(--orange-dark); }

    @keyframes shimmer { from { background-position: 100% 0; } to { background-position: 0 0; } }
    @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

    @media (max-width: 960px) {
      .hero-panel { grid-template-columns: 1fr; padding: 44px; }
      .hero-copy > p { max-width: 700px; }
      .restaurant-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    @media (max-width: 680px) {
      .shell { width: min(100% - 24px, 1180px); }
      .nav { min-height: 68px; }
      .service-state, .brand-copy small { display: none; }
      .nav-actions .button { width: 43px; min-height: 43px; padding: 0; }
      .nav-actions .button span { display: none; }
      .hero { padding-top: 18px; }
      .hero-panel { min-height: 0; gap: 30px; padding: 32px 22px; border-radius: 26px; }
      h1 { font-size: clamp(2.45rem, 13vw, 3.6rem); }
      .hero-stats { gap: 18px 28px; }
      .recommend-box { padding: 20px; }
      .field-row, .toolbar, .form-grid { grid-template-columns: 1fr; }
      .content { padding-top: 38px; }
      .section-head { align-items: start; flex-direction: column; gap: 7px; }
      .restaurant-grid { grid-template-columns: 1fr; }
      .restaurant-card { min-height: 255px; }
      .dialog-body { padding: 22px; }
      .footer-inner { align-items: start; flex-direction: column; }
    }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
    }
  </style>
</head>
<body>
  <header class="site-header">
    <nav class="shell nav" aria-label="主要導覽">
      <a class="brand" href="/" aria-label="莫名起妙首頁">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 3v7c0 2 1.5 3.5 3.5 3.5V21M8.5 3v7M12 3v7M17 3c-2 0-3 2.6-3 5.5s1.2 4.5 3 5V21M17 3v18"/></svg>
        </span>
        <span class="brand-copy"><strong>莫名起妙不要問我要吃啥</strong><small>CHOOSEAT</small></span>
      </a>
      <div class="nav-actions">
        <span class="service-state">服務正常</span>
        <button class="button" type="button" onclick="openRestaurantDialog()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
          <span>新增餐廳</span>
        </button>
      </div>
    </nav>
  </header>

  <main>
    <section class="hero">
      <div class="shell hero-panel">
        <div class="hero-copy">
          <span class="eyebrow">你的用餐靈感</span>
          <h1>等一下要吃什麼</h1>
          <p>大學生每天最大的煩惱</p>
          <div class="hero-stats" aria-label="餐廳統計">
            <div class="hero-stat"><strong id="totalCount">—</strong><span>間精選餐廳</span></div>
            <div class="hero-stat"><strong id="openCount">—</strong><span>間目前營業</span></div>
            <div class="hero-stat"><strong id="categoryCount">—</strong><span>種美食分類</span></div>
          </div>
        </div>

        <aside class="recommend-box" aria-labelledby="recommendTitle">
          <div class="recommend-heading">
            <div><span class="category">QUICK PICK</span><h2 id="recommendTitle">我來幫你選</h2></div>
            <span class="dice" aria-hidden="true">✦</span>
          </div>
          <div class="field-row">
            <div class="field">
              <label for="recommendCategory">今天想吃</label>
              <select id="recommendCategory"><option value="">都可以</option></select>
            </div>
            <div class="field">
              <label for="recommendPrice">最高價位</label>
              <select id="recommendPrice">
                <option value="">不限預算</option>
                <option value="1">$・輕鬆吃</option>
                <option value="2">$$・好好吃</option>
                <option value="3">$$$・犒賞一下</option>
              </select>
            </div>
          </div>
          <button id="recommendButton" class="button" type="button" onclick="getRecommendation()">
            <span>幫我選一家</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 17h4l3-10h2l3 10h4M9 14h6"/></svg>
          </button>
          <div id="recommendResult" class="recommend-result" aria-live="polite"></div>
        </aside>
      </div>
    </section>

    <section class="content" id="restaurantsSection">
      <div class="shell">
        <div class="section-head">
          <div><h2>探索好味道</h2><p>每一餐，都值得有個好選擇。</p></div>
          <span id="resultCount" class="result-count">正在整理餐廳…</span>
        </div>

        <div class="toolbar" aria-label="餐廳篩選">
          <div class="search-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
            <input id="searchInput" type="search" placeholder="搜尋餐廳名稱" aria-label="搜尋餐廳名稱">
          </div>
          <select id="categoryFilter" aria-label="依食物類型篩選"><option value="">所有類型</option></select>
          <select id="openFilter" aria-label="依營業狀態篩選">
            <option value="true">營業中</option>
            <option value="">全部狀態</option>
            <option value="false">休息中</option>
          </select>
        </div>

        <div id="restaurantGrid" class="restaurant-grid" aria-live="polite">
          <div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <div class="shell footer-inner">
      <span>莫名起妙 不用再煩惱等一下要吃什麼</span>
      <a href="/docs" target="_blank" rel="noreferrer">開發者文件</a>
    </div>
  </footer>

  <dialog id="restaurantDialog" aria-labelledby="dialogTitle">
    <form id="restaurantForm" class="dialog-body">
      <div class="dialog-head">
        <div><h2 id="dialogTitle">收藏新餐廳</h2><p id="dialogSubtitle">把下一間想吃的店放進口袋名單。</p></div>
        <button class="icon-button" type="button" onclick="closeRestaurantDialog()" aria-label="關閉">×</button>
      </div>
      <input id="restaurantId" type="hidden">
      <div class="form-stack">
        <div class="field">
          <label for="restaurantName">餐廳名稱</label>
          <input id="restaurantName" name="name" maxlength="100" required placeholder="例如：巷口牛肉麵">
        </div>
        <div class="field">
          <label for="restaurantCategory">食物類型</label>
          <input id="restaurantCategory" name="category" maxlength="50" required list="categorySuggestions" placeholder="例如：中式、日式、早午餐">
          <datalist id="categorySuggestions"></datalist>
        </div>
        <div class="field">
          <label>價位等級</label>
          <div class="price-options">
            <label><input type="radio" name="price_level" value="1" required><span>$<br>輕鬆吃</span></label>
            <label><input type="radio" name="price_level" value="2"><span>$$<br>好好吃</span></label>
            <label><input type="radio" name="price_level" value="3"><span>$$$<br>犒賞一下</span></label>
          </div>
        </div>
        <div class="switch-row">
          <div><strong>目前營業中</strong><small>關閉後仍會保留在收藏清單</small></div>
          <label class="switch"><input id="restaurantOpen" name="is_open" type="checkbox" checked><span></span></label>
        </div>
      </div>
      <div id="formError" class="dialog-error" role="alert"></div>
      <div class="dialog-actions">
        <button class="button secondary" type="button" onclick="closeRestaurantDialog()">取消</button>
        <button id="saveButton" class="button" type="submit">儲存餐廳</button>
      </div>
    </form>
  </dialog>

  <dialog id="deleteDialog" aria-labelledby="deleteTitle">
    <div class="dialog-body">
      <div class="dialog-head">
        <div><h2 id="deleteTitle">移除這間餐廳？</h2><p>這個動作無法復原。</p></div>
        <button class="icon-button" type="button" onclick="closeDeleteDialog()" aria-label="關閉">×</button>
      </div>
      <p class="delete-copy">確定要從收藏中移除 <strong id="deleteRestaurantName"></strong> 嗎？</p>
      <div class="dialog-actions">
        <button class="button secondary" type="button" onclick="closeDeleteDialog()">先保留</button>
        <button class="button danger" type="button" onclick="confirmDelete()">確認移除</button>
      </div>
    </div>
  </dialog>

  <div id="toast" class="toast" role="status" aria-live="polite"></div>

  <script>
    const state = { all: [], visible: [], deleteId: null };
    const categoryFilter = document.getElementById('categoryFilter');
    const openFilter = document.getElementById('openFilter');
    const searchInput = document.getElementById('searchInput');
    const restaurantGrid = document.getElementById('restaurantGrid');
    const restaurantDialog = document.getElementById('restaurantDialog');
    const deleteDialog = document.getElementById('deleteDialog');

    function escapeHTML(value) {
      return String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
    }

    function foodEmoji(category) {
      const value = category.toLowerCase();
      if (/日式|壽司|拉麵/.test(value)) return '🍣';
      if (/韓式|韓國/.test(value)) return '🍲';
      if (/義式|披薩|義大利/.test(value)) return '🍕';
      if (/美式|漢堡/.test(value)) return '🍔';
      if (/甜點|下午茶|蛋糕/.test(value)) return '🍰';
      if (/咖啡|飲料/.test(value)) return '☕';
      if (/早餐|早午餐/.test(value)) return '🥐';
      if (/火鍋/.test(value)) return '🥘';
      if (/中式|台式|麵|小吃/.test(value)) return '🥢';
      return '🍽️';
    }

    function priceLabel(level) {
      return `${'$'.repeat(level)}・${['輕鬆吃', '好好吃', '犒賞一下'][level - 1]}`;
    }

    async function api(path, options = {}) {
      const response = await fetch(path, { headers: {'Content-Type': 'application/json'}, ...options });
      if (response.status === 204) return null;
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map(item => item.msg).join('、')
          : data.detail || '目前無法完成操作，請稍後再試。';
        throw new Error(detail);
      }
      return data;
    }

    async function refreshRestaurants() {
      restaurantGrid.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
      try {
        state.all = await api('/restaurants');
        updateCategories();
        updateStats();
        applyFilters();
      } catch (error) {
        restaurantGrid.innerHTML = `<div class="empty-state"><div class="empty-icon">!</div><h3>暫時連不上餐廳清單</h3><p>${escapeHTML(error.message)}</p></div>`;
        document.getElementById('resultCount').textContent = '載入失敗';
      }
    }

    function updateStats() {
      const categories = new Set(state.all.map(item => item.category));
      document.getElementById('totalCount').textContent = state.all.length;
      document.getElementById('openCount').textContent = state.all.filter(item => item.is_open).length;
      document.getElementById('categoryCount').textContent = categories.size;
    }

    function updateCategories() {
      const currentFilter = categoryFilter.value;
      const currentRecommend = document.getElementById('recommendCategory').value;
      const categories = [...new Set(state.all.map(item => item.category))].sort((a, b) => a.localeCompare(b, 'zh-Hant'));
      const options = categories.map(item => `<option value="${escapeHTML(item)}">${escapeHTML(item)}</option>`).join('');
      categoryFilter.innerHTML = `<option value="">所有類型</option>${options}`;
      document.getElementById('recommendCategory').innerHTML = `<option value="">都可以</option>${options}`;
      document.getElementById('categorySuggestions').innerHTML = options;
      if (categories.includes(currentFilter)) categoryFilter.value = currentFilter;
      if (categories.includes(currentRecommend)) document.getElementById('recommendCategory').value = currentRecommend;
    }

    function applyFilters() {
      const keyword = searchInput.value.trim().toLowerCase();
      const category = categoryFilter.value;
      const openValue = openFilter.value;
      state.visible = state.all.filter(item => {
        const matchesName = item.name.toLowerCase().includes(keyword);
        const matchesCategory = !category || item.category === category;
        const matchesOpen = openValue === '' || item.is_open === (openValue === 'true');
        return matchesName && matchesCategory && matchesOpen;
      });
      renderRestaurants();
    }

    function renderRestaurants() {
      document.getElementById('resultCount').textContent = `找到 ${state.visible.length} 間餐廳`;
      if (!state.visible.length) {
        restaurantGrid.innerHTML = `<div class="empty-state"><div class="empty-icon">🍽️</div><h3>這裡還沒有符合的餐廳</h3><p>換個篩選條件，或收藏一間新的口袋名單。</p></div>`;
        return;
      }
      restaurantGrid.innerHTML = state.visible.map(item => `
        <article class="restaurant-card">
          <div class="card-top">
            <span class="food-icon" aria-hidden="true">${foodEmoji(item.category)}</span>
            <span class="status-pill ${item.is_open ? '' : 'closed'}">${item.is_open ? '營業中' : '休息中'}</span>
          </div>
          <div class="card-copy">
            <span class="category">${escapeHTML(item.category)}</span>
            <h3 title="${escapeHTML(item.name)}">${escapeHTML(item.name)}</h3>
            <div class="price">價位 <strong>${escapeHTML(priceLabel(item.price_level))}</strong></div>
          </div>
          <div class="card-actions">
            <button class="text-button" type="button" onclick="openEditDialog(${item.id})">編輯資訊</button>
            <button class="text-button delete" type="button" onclick="openDeleteDialog(${item.id})">移除</button>
          </div>
        </article>`).join('');
    }

    function openRestaurantDialog() {
      document.getElementById('restaurantForm').reset();
      document.getElementById('restaurantId').value = '';
      document.getElementById('restaurantOpen').checked = true;
      document.getElementById('dialogTitle').textContent = '收藏新餐廳';
      document.getElementById('dialogSubtitle').textContent = '把下一間想吃的店放進口袋名單。';
      document.getElementById('saveButton').textContent = '儲存餐廳';
      setFormError('');
      restaurantDialog.showModal();
      setTimeout(() => document.getElementById('restaurantName').focus(), 50);
    }

    function openEditDialog(id) {
      const item = state.all.find(restaurant => restaurant.id === id);
      if (!item) return;
      document.getElementById('restaurantId').value = item.id;
      document.getElementById('restaurantName').value = item.name;
      document.getElementById('restaurantCategory').value = item.category;
      document.querySelector(`input[name="price_level"][value="${item.price_level}"]`).checked = true;
      document.getElementById('restaurantOpen').checked = item.is_open;
      document.getElementById('dialogTitle').textContent = '編輯餐廳資訊';
      document.getElementById('dialogSubtitle').textContent = '更新後會立即同步到餐廳清單。';
      document.getElementById('saveButton').textContent = '儲存變更';
      setFormError('');
      restaurantDialog.showModal();
    }

    function closeRestaurantDialog() { restaurantDialog.close(); }
    function setFormError(message) {
      const element = document.getElementById('formError');
      element.textContent = message;
      element.classList.toggle('show', Boolean(message));
    }

    document.getElementById('restaurantForm').addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.currentTarget;
      const data = new FormData(form);
      const id = document.getElementById('restaurantId').value;
      const payload = {
        name: data.get('name'),
        category: data.get('category'),
        price_level: Number(data.get('price_level')),
        is_open: document.getElementById('restaurantOpen').checked
      };
      const saveButton = document.getElementById('saveButton');
      saveButton.disabled = true;
      saveButton.textContent = '儲存中…';
      setFormError('');
      try {
        await api(id ? `/restaurants/${id}` : '/restaurants', {
          method: id ? 'PATCH' : 'POST',
          body: JSON.stringify(payload)
        });
        closeRestaurantDialog();
        showToast(id ? '餐廳資訊已更新' : '餐廳已加入收藏');
        await refreshRestaurants();
      } catch (error) {
        setFormError(error.message);
      } finally {
        saveButton.disabled = false;
        saveButton.textContent = id ? '儲存變更' : '儲存餐廳';
      }
    });

    function openDeleteDialog(id) {
      const item = state.all.find(restaurant => restaurant.id === id);
      if (!item) return;
      state.deleteId = id;
      document.getElementById('deleteRestaurantName').textContent = item.name;
      deleteDialog.showModal();
    }

    function closeDeleteDialog() { state.deleteId = null; deleteDialog.close(); }

    async function confirmDelete() {
      if (state.deleteId === null) return;
      const id = state.deleteId;
      try {
        await api(`/restaurants/${id}`, {method: 'DELETE'});
        closeDeleteDialog();
        showToast('餐廳已從收藏中移除');
        await refreshRestaurants();
      } catch (error) {
        showToast(error.message, true);
      }
    }

    async function getRecommendation() {
      const button = document.getElementById('recommendButton');
      const result = document.getElementById('recommendResult');
      const params = new URLSearchParams();
      const category = document.getElementById('recommendCategory').value;
      const maxPrice = document.getElementById('recommendPrice').value;
      if (category) params.set('category', category);
      if (maxPrice) params.set('max_price_level', maxPrice);
      button.disabled = true;
      button.querySelector('span').textContent = '正在挑選…';
      try {
        const item = await api(`/recommend${params.size ? `?${params}` : ''}`);
        result.innerHTML = `<span class="result-emoji">${foodEmoji(item.category)}</span><span class="result-copy"><small>今天就吃這間</small><strong>${escapeHTML(item.name)}</strong></span>`;
        result.classList.add('show');
      } catch (error) {
        result.innerHTML = `<span class="result-emoji">🥲</span><span class="result-copy"><small>暫時選不到</small><strong>${escapeHTML(error.message)}</strong></span>`;
        result.classList.add('show');
      } finally {
        button.disabled = false;
        button.querySelector('span').textContent = '再選一家';
      }
    }

    let toastTimer;
    function showToast(message, isError = false) {
      const toast = document.getElementById('toast');
      clearTimeout(toastTimer);
      toast.textContent = message;
      toast.classList.toggle('error', isError);
      toast.classList.add('show');
      toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
    }

    [categoryFilter, openFilter].forEach(element => element.addEventListener('change', applyFilters));
    searchInput.addEventListener('input', applyFilters);
    restaurantDialog.addEventListener('click', event => { if (event.target === restaurantDialog) closeRestaurantDialog(); });
    deleteDialog.addEventListener('click', event => { if (event.target === deleteDialog) closeDeleteDialog(); });
    refreshRestaurants();
  </script>
</body>
</html>"""


app = FastAPI(
    title="今天吃什麼 API",
    description="使用 FastAPI、SQLModel 與 SQLite 管理餐廳，並隨機推薦目前營業中的餐廳。",
    version="1.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "餐廳", "description": "餐廳資料的新增、查詢、更新與刪除。"},
        {"name": "推薦", "description": "依條件隨機推薦目前營業中的餐廳。"},
    ],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home_page() -> HTMLResponse:
    """回傳一般使用者操作餐廳平台的首頁。"""

    return HTMLResponse(content=HOME_PAGE)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """提供瀏覽器頁籤圖示，避免 favicon 請求產生 404。"""

    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


@app.post(
    "/restaurants",
    response_model=RestaurantRead,
    status_code=status.HTTP_201_CREATED,
    tags=["餐廳"],
    summary="新增餐廳",
    description="驗證輸入資料後，將一筆新餐廳寫入 SQLite restaurants 資料表。",
)
def create_restaurant(
    restaurant_data: RestaurantCreate,
    session: Session = Depends(get_session),
) -> Restaurant:
    restaurant = Restaurant.model_validate(restaurant_data)
    session.add(restaurant)
    session.commit()
    session.refresh(restaurant)
    return restaurant


@app.get(
    "/restaurants",
    response_model=list[RestaurantRead],
    tags=["餐廳"],
    summary="取得餐廳清單",
    description="取得所有餐廳；可使用 category 與 is_open 查詢參數同時篩選。",
)
def list_restaurants(
    category: str | None = Query(default=None, description="食物類型（完全相符）"),
    is_open: bool | None = Query(default=None, description="是否營業中"),
    session: Session = Depends(get_session),
) -> list[Restaurant]:
    statement = select(Restaurant)
    if category is not None:
        statement = statement.where(Restaurant.category == category)
    if is_open is not None:
        statement = statement.where(Restaurant.is_open == is_open)
    return list(session.exec(statement).all())


@app.get(
    "/restaurants/{id}",
    response_model=RestaurantRead,
    tags=["餐廳"],
    summary="取得單一餐廳",
    description="依餐廳 id 取得資料；指定 id 不存在時回傳 404。",
)
def read_restaurant(
    id: int,
    session: Session = Depends(get_session),
) -> Restaurant:
    return get_restaurant_or_404(id, session)


@app.patch(
    "/restaurants/{id}",
    response_model=RestaurantRead,
    tags=["餐廳"],
    summary="部分更新餐廳",
    description="只更新 request body 中有提供的欄位；指定 id 不存在時回傳 404。",
)
def update_restaurant(
    id: int,
    restaurant_data: RestaurantUpdate,
    session: Session = Depends(get_session),
) -> Restaurant:
    restaurant = get_restaurant_or_404(id, session)
    update_data = restaurant_data.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(restaurant, field_name, value)
    session.add(restaurant)
    session.commit()
    session.refresh(restaurant)
    return restaurant


@app.delete(
    "/restaurants/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["餐廳"],
    summary="刪除餐廳",
    description="依餐廳 id 刪除資料；成功時回傳 204，指定 id 不存在時回傳 404。",
)
def delete_restaurant(
    id: int,
    session: Session = Depends(get_session),
) -> Response:
    restaurant = get_restaurant_or_404(id, session)
    session.delete(restaurant)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/recommend",
    response_model=RestaurantRead,
    tags=["推薦"],
    summary="隨機推薦餐廳",
    description="從目前營業中且符合 category、max_price_level 條件的餐廳隨機推薦一家；無符合資料時回傳 404。",
)
def recommend_restaurant(
    category: str | None = Query(default=None, description="食物類型（完全相符）"),
    max_price_level: int | None = Query(
        default=None,
        ge=1,
        le=3,
        description="可接受的最高價位等級（1 到 3）",
    ),
    session: Session = Depends(get_session),
) -> Restaurant:
    statement = select(Restaurant).where(Restaurant.is_open == True)  # noqa: E712
    if category is not None:
        statement = statement.where(Restaurant.category == category)
    if max_price_level is not None:
        statement = statement.where(Restaurant.price_level <= max_price_level)

    statement = statement.order_by(func.random()).limit(1)
    restaurant = session.exec(statement).first()
    if restaurant is None:
        raise HTTPException(status_code=404, detail="沒有符合推薦條件的餐廳")
    return restaurant
