#!/bin/sh

JAVA_VERSION=14.0.2
JAVA=/opt/java/bin/java

GO_VERSION=1.15

OPENAPI_GEN_VERSION=4.3.1
OPENAPI_GEN=/opt/openapi-gen.jar

BASE_YAML=api/info.yaml
OPENAPI_YAML=openapi.yaml
OPENAPI_JSON=openapi.json

GO_CLIENT_PKG=otgclient
GO_CLIENT_DIR=goclient

# Avoid warnings for non-interactive apt-get install
export DEBIAN_FRONTEND=noninteractive

get_java() {
    mkdir -p /opt/java
    curl -kL https://download.java.net/java/GA/jdk${JAVA_VERSION}/205943a0976c4ed48cb16f1043c5c647/12/GPL/openjdk-${JAVA_VERSION}_linux-x64_bin.tar.gz \
        | tar --strip-components 1 -C /opt/java -xzf -
}

get_go() {
    echo "\nInstalling Go ...\n"
    # install golang per https://golang.org/doc/install#tarball
    curl -kL https://dl.google.com/go/go${GO_VERSION}.linux-amd64.tar.gz \
        | tar -C /usr/local/ -xzf -
}

get_go_deps() {
    echo "\nDowloading go dependencies ...\n"
    # for generating Go client stubs from openapi.yaml
    GO111MODULE=on /usr/local/go/bin/go get github.com/deepmap/oapi-codegen/cmd/oapi-codegen@v1.3.13
}

get_openapi_gen() {
    curl -kL -o ${OPENAPI_GEN} https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli/${OPENAPI_GEN_VERSION}/openapi-generator-cli-${OPENAPI_GEN_VERSION}.jar
}

install_deps() {
    apt-get update \
    && apt-get -y install --no-install-recommends apt-utils dialog 2>&1 \
    && apt-get -y install curl git python-is-python3 python3-pip \
    && python -m pip install -r requirements.txt \
    && get_go \
    && get_go_deps
}

gen_open_api() {
    echo "\nGenerating Open API v3 YAML/JSON ...\n"
    python build.py
}

gen_goclient() {
    echo "\nGenerating Go stubs from OpenAPI v3 spec ...\n"
    rm -rf ${GO_CLIENT_DIR} && mkdir -p ${GO_CLIENT_DIR}
    ${GOPATH}/bin/oapi-codegen \
        -generate "types,client" \
        -package "${GO_CLIENT_PKG}" \
        ${OPENAPI_YAML} > ${GO_CLIENT_DIR}/client.go
}

gen_stubs() {
    gen_goclient
}

gen_spec() {
    gen_open_api
}

create_artifacts() {
    # also creates a file named tag containing version if the version isn't
    # already tagged
    version=$(get_version)
    tar czvf art/${GO_CLIENT_DIR}.tar.gz ${GO_CLIENT_DIR} \
    && tar czvf protobuf3.tar.gz art/otg/otg_pb2* \
    && rm -rf art/otg
}

get_version() {
    grep version ${BASE_YAML} | cut -d: -f2 | sed -e "s/\s//g"
}

update_version() {
    version=$1

    echo "Upgrading version to $version ..."
    for f in $(find . -type f -name "*.yaml")
    do
        sed -i "s/version.*/version: ${version}/g" ${f}
    done
}

clean() {
    rm -rf art ${GO_CLIENT_DIR}
}

case $1 in
    deps   )
        install_deps
        ;;
    spec )
        gen_spec
        ;;
    gen  )
        gen_stubs
        ;;
    art  )
        gen_spec && gen_stubs && create_artifacts
        ;;
    version  )
        echo $(get_version)
        ;;
    clean )
        clean
        ;;
    *   )
        $1 || echo "usage: $0 [deps|spec|gen|art|clean|version]"
        ;;
esac
