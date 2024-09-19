FROM node:20.12.1-slim

# Set the working directory in the container
WORKDIR /app

# Copy package.json and install dependencies
COPY package.json ./
RUN npm install
RUN npm install -g nodemon

# Copy the rest of the application
COPY . .

# Expose port 3000
EXPOSE 3000

# Use CMD for development
CMD ["npm", "run", "dev"]
