import json
from pathlib import Path



def save_json(data, filename):


    output_path = (

        Path(__file__)
        .parent
        .parent
        /
        "outputs"
        /
        filename

    )


    output_path.parent.mkdir(
        exist_ok=True
    )


    with open(

        output_path,

        "w",

        encoding="utf-8"

    ) as f:


        json.dump(

            data,

            f,

            ensure_ascii=False,

            indent=4

        )


    return output_path