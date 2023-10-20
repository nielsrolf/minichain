# Build the frontend
cd minichain-ui/
npm run build/
cd ..

# Build the backend
export VERSION='latest'
docker buildx build --platform linux/amd64,linux/arm64 -t nielsrolf/minichain:$VERSION .
docker buildx build --platform linux/amd64,linux/arm64 -t nielsrolf/minichain:$VERSION . --push



# Push the backend
docker buildx build --push --tag nielsrolf/minichain:$VERSION --platform=linux/arm64,linux/amd64 .

# Deploy the backend
git push dokku main

# Build the VSCode extension
cd minichain-vscode/
vsce package
cd ..