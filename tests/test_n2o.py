from n2o import main


def test_main_runs(capsys):
    main()
    captured = capsys.readouterr()
    assert "neural-to-output" in captured.out
