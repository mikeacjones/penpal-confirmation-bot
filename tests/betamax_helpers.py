from betamax.cassette import cassette
from betamax import Betamax
import json
import functools


def sanitize_cassette(interaction, current_cassette):
    # Exit early if the request did not return 200 OK because that's the
    # only time we want to look for Authorization-Token headers
    if interaction.data["response"]["status"]["code"] != 200:
        return

    body = interaction.data["response"]["body"]
    body = body.get("string", "")
    if "access_token" in body:
        body = json.loads(body)
        current_cassette.placeholders.append(
            cassette.Placeholder(
                placeholder=f"<ACCESS-TOKEN>", replace=body["access_token"]
            )
        )

    for headers in [
        interaction.data["request"]["headers"],
        interaction.data["response"]["headers"],
    ]:
        for restricted_header in ["Authorization", "Cookie", "Set-Cookie"]:
            header = headers.get(restricted_header)
            # If there was no token header in the response, exit
            if header is None:
                continue

            # Otherwise, create a new placeholder so that when cassette is saved,
            # Betamax will replace the token with our placeholder.
            for value in header:
                current_cassette.placeholders.append(
                    cassette.Placeholder(
                        placeholder=f"<{restricted_header}>", replace=value
                    )
                )


def use_recorder(func):
    @functools.wraps(func)
    def __call__(*args, **kwargs):
        _recorder = kwargs["recorder"]
        with _recorder.use_cassette(func.__name__):
            return func(*args, **kwargs)

    return __call__
