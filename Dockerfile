FROM ubuntu:20.04
ENV ROOT_PATH=/home/otg/models
ENV GOPATH=/home/go
RUN mkdir -p ${ROOT_PATH}
# Get project source, install dependencies and build it
COPY . ${ROOT_PATH}/
RUN cd ${ROOT_PATH} && chmod +x ./do.sh && ./do.sh deps 2>&1
WORKDIR ${ROOT_PATH}
CMD ["/bin/bash"]
