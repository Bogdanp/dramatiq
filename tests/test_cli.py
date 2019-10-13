from subprocess import PIPE, STDOUT

from .common import skip_in_ci

fakebroker = object()


class BrokerHolder:
    fakebroker = object()


@skip_in_ci
def test_cli_fails_to_start_given_an_invalid_broker_name(start_cli):
    # Given that this module doesn't define a broker called "idontexist"
    # When I start the cli and point it at that broker
    proc = start_cli("tests.test_cli:idontexist", stdout=PIPE, stderr=STDOUT)
    proc.wait(5)

    # Then the process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"Module 'tests.test_cli' does not define a 'idontexist' variable." in proc.stdout.read()


@skip_in_ci
def test_cli_fails_to_start_given_an_invalid_broker_instance(start_cli):
    # Given that this module defines a "fakebroker" variable that's not a Broker
    # When I start the cli and point it at that broker
    proc = start_cli("tests.test_cli:fakebroker", stdout=PIPE, stderr=STDOUT)
    proc.wait(5)

    # Then the process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"'tests.test_cli:fakebroker' is not a Broker." in proc.stdout.read()


@skip_in_ci
def test_cli_fails_to_start_given_an_invalid_nested_broker_instance(start_cli):
    # Given that this module defines a "BrokerHolder.fakebroker" variable that's not a Broker
    # When I start the cli and point it at that broker
    proc = start_cli("tests.test_cli:BrokerHolder.fakebroker", stdout=PIPE, stderr=STDOUT)
    proc.wait(5)

    # Then the process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"'tests.test_cli:BrokerHolder.fakebroker' is not a Broker." in proc.stdout.read()
