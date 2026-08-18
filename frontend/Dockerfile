# Step 1: Build React App
FROM node:18-alpine AS build

WORKDIR /app

# WHY this line: node:18-alpine sets NODE_ENV=production internally,
# which causes npm to silently skip ALL devDependencies during install.
# vite lives in devDependencies -- so without this line, npm installs
# 352 packages but vite is never one of them, causing "sh: vite: not found"
# even though it's listed in package.json.
ENV NODE_ENV=development

# Copy package management files
COPY package*.json ./
RUN npm install

# Copy application source and build
COPY . .
RUN npm run build

# Step 2: Serve with Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]