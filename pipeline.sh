# Build the frontend
cd minichain-ui/
npm run build/
cd ..

# Build the backend
export VERSION='v1.0.4'
docker buildx build --platform linux/amd64,linux/arm64 -t nielsrolf/minichain:$VERSION . --push
docker tag nielsrolf/minichain:$VERSION nielsrolf/minichain:latest
docker push nielsrolf/minichain:latest

# Build the VSCode extension
cd minichain-vscode/
vsce package
cd ..

