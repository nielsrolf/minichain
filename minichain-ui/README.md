
# UI dev setup

By default, the docker image serves both the bundled frontend and the API. For development, you can also start the api without serving the frontend:
```
OPENAI_API_KEY=key REPLICATE_API_TOKEN=key python -m minichain.api
```
And then start the react development server via:
```
cd minichain-ui
npm run start
```

You will need your [OpenAI GPT-4](https://openai.com) and [Replicate](https://replicate.com) keys in your enviroment variables:
