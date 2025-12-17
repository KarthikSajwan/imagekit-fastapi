import streamlit as st
import requests


API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Media Upload App", layout="centered")



if "token" not in st.session_state:
    st.session_state.token = None

if "email" not in st.session_state:
    st.session_state.email = None


def auth_headers():
    return {
        "Authorization": f"Bearer {st.session_state.token}"
    }


def logout():
    st.session_state.token = None
    st.session_state.email = None
    st.rerun()


def show_error(res, fallback="Request failed"):
    """
    Safely display backend errors without crashing Streamlit
    """
    try:
        content_type = res.headers.get("content-type", "")
        if "application/json" in content_type:
            st.error(res.json())
        else:
            st.error(res.text or fallback)
    except Exception:
        st.error(fallback)


st.title("📸 Media Upload App")

if not st.session_state.token:
    tabs = st.tabs(["Login", "Register"])

    # ---------- LOGIN ----------
    with tabs[0]:
        st.subheader("Login")

        # FIX: Wrapped in a form to prevent reload loops and handle "Enter" key
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit_login = st.form_submit_button("Login")

        if submit_login:
            if not email or not password:
                st.warning("Please enter both email and password")
            else:
                try:
                    res = requests.post(
                        f"{API_BASE_URL}/auth/jwt/login",
                        data={
                            "username": email,
                            "password": password,
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )

                    if res.status_code == 200:
                        st.session_state.token = res.json()["access_token"]
                        st.session_state.email = email
                        st.success("Logged in successfully")
                        st.rerun()
                    else:
                        show_error(res, "Login failed")
                except requests.exceptions.ConnectionError:
                    st.error(f"❌ Could not connect to backend at {API_BASE_URL}. Is the server running?")

    # ---------- REGISTER ----------
    with tabs[1]:
        st.subheader("Register")

        # FIX: Wrapped in a form here as well
        with st.form("register_form"):
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            submit_register = st.form_submit_button("Register")

        if submit_register:
            if not reg_email or not reg_password:
                st.warning("Please enter an email and password")
            else:
                try:
                    res = requests.post(
                        f"{API_BASE_URL}/auth/register",
                        json={
                            "email": reg_email,
                            "password": reg_password,
                        },
                    )

                    if res.status_code in (200, 201):
                        st.success("Registration successful. You can now log in.")
                    else:
                        show_error(res, "Registration failed")
                except requests.exceptions.ConnectionError:
                    st.error(f"❌ Could not connect to backend at {API_BASE_URL}.")

    st.stop()


# --------------------------------------------------
# LOGGED IN UI
# --------------------------------------------------
st.sidebar.success(f"Logged in as {st.session_state.email}")
st.sidebar.button("Logout", on_click=logout)

st.header("⬆️ Upload Image / Video")

# We don't strictly need a form here, but it's cleaner for file uploads too
with st.form("upload_form"):
    uploaded_file = st.file_uploader(
        "Choose an image or video",
        type=["jpg", "jpeg", "png", "mp4", "mov"]
    )
    caption = st.text_input("Caption (optional)")
    submit_upload = st.form_submit_button("Upload")

if submit_upload:
    if not uploaded_file:
        st.warning("Please select a file")
    else:
        files = {"file": uploaded_file}
        data = {"caption": caption}

        try:
            res = requests.post(
                f"{API_BASE_URL}/upload",
                headers=auth_headers(),
                files=files,
                data=data,
            )

            if res.status_code == 200:
                st.success("Upload successful")
                # Optional: rerun to show the new post immediately
                # st.rerun() 
            else:
                show_error(res, "Upload failed")
        except requests.exceptions.ConnectionError:
             st.error("❌ Connection error during upload.")


# --------------------------------------------------
# FEED
# --------------------------------------------------
st.divider()
st.header("🖼️ Your Uploads")

try:
    res = requests.get(
        f"{API_BASE_URL}/feed",
        headers=auth_headers(),
    )

    if res.status_code != 200:
        show_error(res, "Failed to fetch posts")
        # Don't stop here, allow the UI to remain visible
    else:
        posts = res.json().get("posts", [])

        if not posts:
            st.info("No uploads yet")
        else:
            for post in posts:
                # Wrap each post in a container for better layout
                with st.container():
                    if post.get("caption"):
                        st.markdown(f"**{post['caption']}**")

                    if post["file_type"] == "image":
                        st.image(post["url"], width="stretch")
                    else:
                        st.video(post["url"])

                    # Buttons inside loops need unique keys
                    if st.button("Delete", key=f"del_{post['id']}"):
                        try:
                            del_res = requests.delete(
                                f"{API_BASE_URL}/posts/{post['id']}",
                                headers=auth_headers(),
                            )

                            if del_res.status_code == 200:
                                st.success("Deleted")
                                st.rerun()
                            else:
                                show_error(del_res, "Delete failed")
                        except requests.exceptions.ConnectionError:
                            st.error("❌ Connection error during deletion.")

                    st.divider()

except requests.exceptions.ConnectionError:
    st.error(f"❌ Could not load feed. Is backend running at {API_BASE_URL}?")