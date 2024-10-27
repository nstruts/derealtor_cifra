image_url = 'https://2594-109-124-228-71.ngrok-free.app/get-image?filename=photo_2024-09-19_20-33-38.jpg'
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Что на этом изображении?"},
        {
          "type": "image_url",
          "image_url": {
            "url": image_url,
            "detail":"high"
          },
        },
      ],
    }
  ],
  max_tokens=300,
)

print(response.choices[0],'\n',
      response.usage.total_tokens)