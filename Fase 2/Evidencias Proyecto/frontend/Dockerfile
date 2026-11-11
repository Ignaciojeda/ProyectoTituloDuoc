FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# --host 0.0.0.0 es obligatorio para que el navegador de tu PC llegue al contenedor
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
