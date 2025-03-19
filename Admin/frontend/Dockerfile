# Build the React App
FROM node:16-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
RUN npm install react-spinners react-pdf react-toastify


COPY . .
RUN npm run build

# Serve with Nginx
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
