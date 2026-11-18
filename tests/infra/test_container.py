"""Testinfra: перевірка запущеного контейнера.

Запуск: pytest tests/infra --hosts=docker://devops7-app
"""
import pytest

APP_USER = "app"
PORT_HEX = "1F40"  # 8000 у шістнадцятковому вигляді


@pytest.mark.parametrize("path", ["/app/app.py", "/app/requirements.txt"])
def test_app_files_exist(host, path):
    f = host.file(path)
    assert f.exists
    assert f.is_file


def test_data_dir_belongs_to_app_user(host):
    d = host.file("/app/data")
    assert d.is_directory
    assert d.user == APP_USER


def test_main_process_is_gunicorn(host):
    cmdline = host.file("/proc/1/cmdline").content_string
    assert "gunicorn" in cmdline


def test_main_process_is_not_root(host):
    assert host.file("/proc/1").user == APP_USER
    assert host.check_output("id -u") != "0"


def test_port_8000_is_listening(host):
    tcp = host.file("/proc/net/tcp").content_string
    assert f"00000000:{PORT_HEX} 00000000:0000 0A" in tcp


def test_health_inside_container(host):
    cmd = host.run(
        "python -c \"import urllib.request; "
        "print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read().decode())\""
    )
    assert cmd.rc == 0
    assert '"ok"' in cmd.stdout
