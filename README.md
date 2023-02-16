Commands to run in a terminal that's set to this working directory

```console
sudo docker build --network=host --tag potatunes-be .
sudo docker run --publish 5000:5000 potatunes-be
```
