from dotenv import load_dotenv
from imagekitio import ImageKit
import os

load_dotenv()

print("DEBUG PUBLIC:", os.getenv("IMAGEKIT_PUBLIC_KEY"))
print("DEBUG PRIVATE:", os.getenv("IMAGEKIT_PRIVATE_KEY"))
print("DEBUG URL:", os.getenv("IMAGEKIT_URL"))


imagekit = ImageKit(
    private_key=os.getenv("IMAGEKIT_PRIVATE_KEY"),
    public_key=os.getenv("IMAGEKIT_PUBLIC_KEY"),
    url_endpoint=os.getenv("IMAGEKIT_URL")
)
