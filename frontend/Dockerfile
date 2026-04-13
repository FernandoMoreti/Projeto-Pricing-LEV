FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm install

COPY . .

EXPOSE 60000

RUN npm run build
CMD ["npm", "run", "start"]