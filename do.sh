#!/bin/sh

JAVA_VERSION=14.0.2
JAVA=/opt/java/bin/java

OPENAPI_GEN_VERSION=4.3.1
OPENAPI_GEN=/opt/openapi-gen.jar

BASE_YAML=api/api.yaml
OPENAPI_YAML=openapi.yaml
OPENAPI_JSON=openapi.json

OPENAPI_PROTO_PKG=athena
PROTO_DIR=protobuf3

PY_CLIENT_PKG=athena
PY_CLIENT_DIR=pyclient

GO_CLIENT_PKG=athena
GO_CLIENT_DIR=goclient

GO_SERVER_PKG=skltn
GO_SERVER_DIR=goserver
GO_SERVER_PORT=443

# Avoid warnings for non-interactive apt-get install
export DEBIAN_FRONTEND=noninteractive

get_java() {
    mkdir -p /opt/java
    curl -kL https://download.java.net/java/GA/jdk${JAVA_VERSION}/205943a0976c4ed48cb16f1043c5c647/12/GPL/openjdk-${JAVA_VERSION}_linux-x64_bin.tar.gz \
        | tar --strip-components 1 -C /opt/java -xzf -
}

get_openapi_gen() {
    curl -kL -o ${OPENAPI_GEN} https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli/${OPENAPI_GEN_VERSION}/openapi-generator-cli-${OPENAPI_GEN_VERSION}.jar
}

install_deps() {
    apt-get update \
    && apt-get -y install --no-install-recommends apt-utils dialog 2>&1 \
    && apt-get -y install curl git python3 python3-pip \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && ln -s /usr/bin/pip3 /usr/bin/pip \
    && python -m pip install flake8 \
    && get_java \
    && get_openapi_gen
}

gen_open_api() {
    jsonout=jsonout
    rm -rf ${jsonout} && mkdir -p ${jsonout}
    echo "\nGenerating Open API v3 YAML ...\n"
    python bundler.py \
    && echo "\nGenerating Open API v3 JSON ...\n" \
    && ${JAVA} -jar ${OPENAPI_GEN} generate -g openapi -i ${OPENAPI_YAML} -o ${jsonout} \
    && mv -f ${jsonout}/openapi.json ${OPENAPI_JSON} \
    && rm -rf ${jsonout}
}

gen_proto() {
    echo "\nGenerating Proto 3 files from Open API v3 YAML ...\n"
    rm -rf ${PROTO_DIR} && mkdir -p ${PROTO_DIR} \
    && ${JAVA} -jar ${OPENAPI_GEN} generate -g protobuf-schema \
        -i ${OPENAPI_YAML} -o ${PROTO_DIR} --package-name ${OPENAPI_PROTO_PKG}
}

gen_pyclient() {
    echo "\nGenerating Python stubs from OpenAPI v3 spec ...\n"
    rm -rf ${PY_CLIENT_DIR} && mkdir -p ${PY_CLIENT_DIR}
    # https://openapi-generator.tech/docs/generators/python/
    ${JAVA} -jar ${OPENAPI_GEN} generate    \
        -i ${OPENAPI_YAML}                  \
        -g python                           \
        -o ${PY_CLIENT_DIR}                 \
        --additional-properties=packageName=${PY_CLIENT_PKG},packageVersion=$(get_version)
}

gen_goclient() {
    echo "\nGenerating Go stubs from OpenAPI v3 spec ...\n"
    rm -rf ${GO_CLIENT_DIR} && mkdir -p ${GO_CLIENT_DIR}
    # https://openapi-generator.tech/docs/generators/go/
    ${JAVA} -jar ${OPENAPI_GEN} generate    \
        -i ${OPENAPI_YAML}                  \
        -g go                               \
        -o ${GO_CLIENT_DIR}                 \
        --additional-properties=packageName=${GO_CLIENT_PKG},packageVersion=$(get_version)
}

gen_goserver() {
    echo "\nGenerating Go skeleton from OpenAPI v3 spec ...\n"
    rm -rf ${GO_SERVER_DIR} && mkdir -p ${GO_SERVER_DIR}
    # https://openapi-generator.tech/docs/generators/go-server/
    ${JAVA} -jar ${OPENAPI_GEN} generate    \
        -i ${OPENAPI_YAML}                  \
        -g go-server                        \
        -o ${GO_SERVER_DIR}                 \
        --additional-properties=packageName=${GO_SERVER_PKG},packageVersion=$(get_version),serverPort=${GO_SERVER_PORT},sourceFolder=${GO_SERVER_PKG}
}

gen_stubs() {
    gen_pyclient \
    && gen_goclient \
    && gen_goserver
}

gen_spec() {
    gen_open_api \
    && gen_proto
}

create_artifacts() {
    # also creates a file named tag containing version if the version isn't
    # alreadt tagged
    version=$(get_version)
    mkdir -p artifacts \
    && cp ${OPENAPI_YAML} artifacts/ \
    && cp ${OPENAPI_JSON} artifacts/ \
    && tar czvf artifacts/${PY_CLIENT_DIR}.tar.gz ${PY_CLIENT_DIR} \
    && tar czvf artifacts/${GO_CLIENT_DIR}.tar.gz ${GO_CLIENT_DIR} \
    && tar czvf artifacts/${GO_SERVER_DIR}.tar.gz ${GO_SERVER_DIR} \
    && tar czvf artifacts/${PROTO_DIR}.tar.gz ${PROTO_DIR} \
    && git rev-parse "v${version}" >/dev/null 2>&1 || echo $version > artifacts/tag
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
    rm -rf \
        ${OPENAPI_YAML} \
        ${OPENAPI_JSON} \
        ${PROTO_DIR} \
        ${PY_CLIENT_DIR} \
        ${GO_CLIENT_DIR} \
        ${GO_SERVER_DIR} \
        artifacts
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
        update_version $2
        ;;
    clean )
        clean
        ;;
    *   )
        $1 || echo "usage: $0 [deps|spec|gen|art|clean|version]"
        ;;
esac
