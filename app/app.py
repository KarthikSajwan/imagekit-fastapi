from fastapi import FastAPI, HTTPException, UploadFile, File

app = FastAPI()

text_posts = {}

@app.get("/posts")
def get_all_post():
    return text_posts

@app.get("/posts/{id}")
def get_post(id: int):
    if id not in text_posts:
        raise HTTPException(status_code=404, detail = "Post not found")
    
    return text_posts.get(id)