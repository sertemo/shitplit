# Para desplegar la aplicación en un contenedor

docker rm shitplit && docker rmi shitplit
docker build -t shitplit . && \
docker run -p 8501:8501 --name shitplit shitplit:latest