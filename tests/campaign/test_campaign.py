from omega_moderne_client.campaign.campaign import Campaign


def test_load_one_campaign():
    campaign = Campaign.load('http_in_gradle_build')
    assert campaign.name == 'http_in_gradle_build'


def test_load_all_campaigns():
    campaigns = Campaign.load_all()
    assert len(campaigns) >= 6


def test_failure():
    assert False
