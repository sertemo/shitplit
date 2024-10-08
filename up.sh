# Para desplegar la aplicación en un contenedor

docker rm shitplit && docker rmi shitplit
docker build -t shitplit . && \
docker run -p 60751:60751 --name shitplit shitplit:latest