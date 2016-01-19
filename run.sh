#!/usr/bin/env bash

cd `dirname $0`

print_usage() {
  echo "Usage: $0 [test|update] [args]"
  echo "- test [tests]: run the tests"
  echo "- update: update the virtual environment"
  exit 1
}

make_venv() {
  [ -f venv/bin/activate ] || {
    virtualenv venv
  }
}

activate_venv() {
  . venv/bin/activate
}

update_venv() {
  make_venv
  activate_venv
  pip install -U setuptools pip wheel ipython ipdb
  pip install -r requirements/dev.txt
}

run_tests() {
  # run python tests
  nosetests $@
}

main() {
  ACTION=$1
  shift

  case ${ACTION} in
    test)
    activate_venv
    run_tests $@
    ;;

    update)
    update_venv
    ;;

    *)
    print_usage
    ;;
  esac
}

main $@
