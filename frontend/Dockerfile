# Use a Node.js base image
FROM node:18-alpine

# Sets the working directory inside the container
WORKDIR /app

# Copies package.json and install dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# Copies the rest of the frontend codebase
COPY frontend/ .

# Build the React app
RUN npm run build

# Expose the frontend port
EXPOSE 3000

# Start the frontend
CMD ["npm", "start"]
