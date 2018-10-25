from subprocess import PIPE

fakebroker = object()


def test_cli_fails_to_start_given_an_invalid_broker_name(start_cli):
    # Given that this module doesn't define a broker called "idontexist"
    # When I start the cli and point it at that broker
    proc = start_cli("tests.test_cli:idontexist", stdout=PIPE, stderr=PIPE)
    proc.wait(5)

    # Then the process return code should be 2
    assert proc.returncode == 2


def test_cli_fails_to_start_given_an_invalid_broker_instance(start_cli):
    # Given that this module defines a "fakebroker" variable that's not a Broker
    # When I start the cli and point it at that broker
    proc = start_cli("tests.test_cli:fakebroker", stdout=PIPE, stderr=PIPE)
    proc.wait(5)

    # Then the process return code should be 2
    assert proc.returncode == 2
