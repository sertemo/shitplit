# Para desplegar la aplicación en un contenedor

docker rm shitplit && docker rmi shitplit
docker build -t shitplit . && \
docker run -e DB_MONGO='mongodb+srv://sergioDBPython:pythonDBsergio1234%40@pythondbtest.q8zkki8.mongodb.net/?retryWrites=true&w=majority' \
    -p 60751:60751 --name shitplit shitplit:latest