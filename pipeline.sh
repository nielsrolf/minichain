# Build the frontend
cd minichain-ui/
npm run build/
cd ..

# Build the backend
docker build -t nielsrolf/minichain .

# Push the backend
docker push nielsrolf/minichain

# Deploy the backend
git push dokku main

# Build the VSCode extension
cd minichain-vscode/
vsce package
cd ..