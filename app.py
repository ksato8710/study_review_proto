import streamlit as st
from pathlib import Path
import sqlite3, uuid
from datetime import date
from PIL import Image

DB_PATH = Path("data.db")
UPLOAD_DIR = Path("uploads")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""create table if not exists images(
        id text primary key,
        file_path text
    )""")
    cur.execute("""create table if not exists problem_sets(
        id text primary key,
        subject text,
        test_date text,
        test_type text
    )""")
    cur.execute("""create table if not exists problem_set_items(
        set_id text,
        image_id text
    )""")
    conn.commit()
    return conn, cur

def save_uploaded_files(uploaded_files, cur, conn):
    UPLOAD_DIR.mkdir(exist_ok=True)
    for file in uploaded_files:
        iid = str(uuid.uuid4())
        out_path = UPLOAD_DIR / f"{iid}_{file.name}"
        with open(out_path, "wb") as f:
            f.write(file.getbuffer())
        cur.execute("insert or ignore into images values (?,?)", (iid, str(out_path)))
    conn.commit()

st.set_page_config(page_title="Study Review Prototype", layout="wide")
st.title("📚 週末テスト復習システム (超速版)")

conn, cur = init_db()

tab_upload, tab_review = st.tabs(["⬆️ アップロード", "📝 復習する"])

with tab_upload:
    st.header("Step 1: 間違い画像をアップロード")
    uploaded_files = st.file_uploader("画像を複数選択してください (jpg/png)", accept_multiple_files=True, type=["jpg","jpeg","png"])
    if uploaded_files:
        save_uploaded_files(uploaded_files, cur, conn)
        st.success(f"{len(uploaded_files)} 枚を保存しました")

    st.subheader("Step 2: 問題セットを作成 (画像3枚を選んで保存)")
    rows = cur.execute("""select id, file_path from images
                          where id not in (select image_id from problem_set_items)""").fetchall()
    if rows:
        cols = st.columns(3)
        selected = []
        for idx, (iid, fp) in enumerate(rows):
            with cols[idx % 3]:
                st.image(fp, width=180)
                if st.checkbox("選択", key=f"chk_{iid}"):
                    selected.append(iid)
        if len(selected) == 3:
            st.markdown("### セット情報")
            subject = st.selectbox("科目", ["算数","国語","理科","社会","その他"])
            test_type = st.selectbox("テスト種別", ["育成テスト","公開テスト","その他"])
            tdate = st.date_input("テスト日", date.today())
            if st.button("💾 問題セットを保存"):
                set_id = str(uuid.uuid4())
                cur.execute("insert into problem_sets values (?,?,?,?)",
                            (set_id, subject, str(tdate), test_type))
                for iid in selected:
                    cur.execute("insert into problem_set_items values (?,?)", (set_id, iid))
                conn.commit()
                st.success("保存しました！")

with tab_review:
    st.header("問題を解き直す")
    subs = [r[0] for r in cur.execute("select distinct subject from problem_sets").fetchall()]
    if subs:
        subject = st.selectbox("科目を選択", subs)
        dates = [r[0] for r in cur.execute("select distinct test_date from problem_sets where subject=?", (subject,)).fetchall()]
        if dates:
            tdate = st.selectbox("テスト日を選択", dates)
            set_row = cur.execute("select id from problem_sets where subject=? and test_date=?",
                                  (subject, tdate)).fetchone()
            if set_row:
                set_id = set_row[0]
                img_rows = cur.execute("""select file_path from images
                                           where id in (select image_id from problem_set_items where set_id=?)""", (set_id,)).fetchall()
                answers = []
                for idx, (fp,) in enumerate(img_rows):
                    st.image(fp, width=220)
                    ans = st.text_input(f"あなたの答え #{idx+1}", key=f"ans_{idx}")
                    answers.append(ans)
                st.button("提出 (採点は親が確認)", key="submit_btn")
    else:
        st.info("まず問題セットを作成してください。")
