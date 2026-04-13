FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm install

COPY . .

ENV PORT=8080
EXPOSE 8080

RUN npm run build
CMD ["npm", "run", "start", "--", "-p", "8080"]