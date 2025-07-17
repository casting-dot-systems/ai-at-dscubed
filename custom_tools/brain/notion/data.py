from dataclasses import dataclass
from typing import NewType

#

# TODO maybe add role types and name types
notion_user_id_type = NewType("notion_user_id_type", str)
discord_user_id_type = NewType("discord_user_id_type", str)


# TODO need to write functions to automatically keep this up to date


@dataclass
class UserData:
    name: str
    role: str
    notion_id: notion_user_id_type
    discord_id: discord_user_id_type


USER_LIST: list[UserData] = [
    UserData(
        name="Danielle Tran",
        role="External Vice President",
        notion_id=notion_user_id_type("8b352898-aa01-40c8-b813-1d674666ebe5"),
        discord_id=discord_user_id_type("1209415347585945661"),
    ),
    UserData(
        name="Nathan Luo",
        role="AI Director",
        notion_id=notion_user_id_type("f746733c-66cc-4cbc-b553-c5d3f03ed240"),
        discord_id=discord_user_id_type("241085495398891521"),
    ),
    UserData(
        name="Anton Huynh",
        role="Industry Officer",
        notion_id=notion_user_id_type("72af2773-0463-4d0e-bb5d-c6da6d595358"),
        discord_id=discord_user_id_type("238180946174672898"),
    ),
    UserData(
        name="Simon Nguyen",
        role="IT Officer",
        notion_id=notion_user_id_type("cb1ca5d0-944a-462a-b18a-e7686dfa1a08"),
        discord_id=discord_user_id_type("528906746337558528"),
    ),
    UserData(
        name="Teresa Guo",
        role="Marketing Director",
        notion_id=notion_user_id_type("f79ec109-12fa-4ae0-8a6f-f57d78e015d3"),
        discord_id=discord_user_id_type("693294943367856139"),
    ),
    UserData(
        name="Soaham",
        role="Events Officer",
        notion_id=notion_user_id_type("fffb7e1b-36c2-479a-9571-27a24079fde2"),
        discord_id=discord_user_id_type("759645006914256926"),
    ),
    UserData(
        name="RANIA",
        role="Secretary",
        notion_id=notion_user_id_type("b8ce8d09-0dfd-4560-8a05-883249cce948"),
        discord_id=discord_user_id_type("1209833336474833010"),
    ),
    UserData(
        name="Michael Ren",
        role="President",
        notion_id=notion_user_id_type("314ad6eb-dc2e-49b5-8801-4afa0360f39b"),
        discord_id=discord_user_id_type("1138969490432991232"),
    ),
    UserData(
        name="Hannah",
        role="Internal Vice President",
        notion_id=notion_user_id_type("84fa5ffe-2848-48f5-b3d7-21269c644d5c"),
        discord_id=discord_user_id_type("415077608011726868"),
    ),
    UserData(
        name="Dhruv Ajay",
        role="Project Lead",
        notion_id=notion_user_id_type("302a361d-511f-44ba-a728-6cae0661e899"),
        discord_id=discord_user_id_type("577829083866464296"),
    ),
    UserData(
        name="Angus Chan",
        role="Events Officer",
        notion_id=notion_user_id_type("ce23a115-7514-474e-9b12-7a99a7699dfe"),
        discord_id=discord_user_id_type("722032358257197087"),
    ),
    UserData(
        name="Ameya Mahesh",
        role="Project Officer",
        notion_id=notion_user_id_type("9f52eb8c-690a-44cf-9562-6701fe5b70ab"),
        discord_id=discord_user_id_type("597270043935637505"),
    ),
    UserData(
        name="Elyse Lee",
        role="HR Director",
        notion_id=notion_user_id_type("0cd789b6-1545-459a-bc05-1ec885b14ee1"),
        discord_id=discord_user_id_type("426419121362829322"),
    ),
    UserData(
        name="Brian King",
        role="IT Officer",
        notion_id=notion_user_id_type("26ea303a-2f37-49f9-8a5b-42c5ca635cf9"),
        discord_id=discord_user_id_type("729929681834344508"),
    ),
    UserData(
        name="Charmaine",
        role="Events Officer",
        notion_id=notion_user_id_type("eefee9b7-e2e1-43aa-95ee-8b224510114a"),
        discord_id=discord_user_id_type("1215511112515326005"),
    ),
    UserData(
        name="Hayden Ma",
        role="Events Officer",
        notion_id=notion_user_id_type("74c1fb03-539a-4de4-8eb1-38492cbeb143"),
        discord_id=discord_user_id_type("741230223214903387"),
    ),
    UserData(
        name="Jamie Marks",
        role="IT Officer",
        notion_id=notion_user_id_type("0e36fbe3-66f3-484b-922c-ac8c0bca47b6"),
        discord_id=discord_user_id_type("503260447705661440"),
    ),
    UserData(
        name="Nick Muir",
        role="Education Officer",
        notion_id=notion_user_id_type("d9e67f1e-b37c-4bf8-9ab9-81e4a78ecfbc"),
        discord_id=discord_user_id_type("657156788180746260"),
    ),
    UserData(
        name="Paul Su",
        role="IT Officer",
        notion_id=notion_user_id_type("eddb1224-a77e-4aeb-8ca5-6e5be6e5ef8f"),
        discord_id=discord_user_id_type("247593577465511937"),
    ),
    UserData(
        name="Geoffrey Chen",
        role="IT Officer",
        notion_id=notion_user_id_type("a45d963f-32e6-47e1-b7ba-caf40ee8280d"),
        discord_id=discord_user_id_type("963627649748594689"),
    ),
    UserData(
        name="Noah Say",
        role="IT Director",
        notion_id=notion_user_id_type("7e1e7da1-3a93-4e48-8a2a-92fb7703cbe5"),
        discord_id=discord_user_id_type("348017694655643648"),
    ),
    UserData(
        name="Chris Gee",
        role="Industry Officer",
        notion_id=notion_user_id_type("95fb5ae3-5126-4c48-a286-000638821d18"),
        discord_id=discord_user_id_type("890262654034259988"),
    ),
    UserData(
        name="Jesselyn Lim",
        role="Industry Officer",
        notion_id=notion_user_id_type("8b706d61-108c-4468-b058-a9727c852643"),
        discord_id=discord_user_id_type("399205935924510720"),
    ),
    UserData(
        name="Jess Zhao",
        role="HR Director",
        notion_id=notion_user_id_type("31b1c4ca-662e-4bcc-a631-772566865139"),
        discord_id=discord_user_id_type("816184594444451903"),
    ),
    UserData(
        name="Kaylyn Phan",
        role="IT Officer",
        notion_id=notion_user_id_type("c8f6b4d6-f7fc-4d04-8a67-706be192b80d"),
        discord_id=discord_user_id_type("437985276892282880"),
    ),
    UserData(
        name="Ethan Cheng",
        role="Industry Officer",
        notion_id=notion_user_id_type("ea42ea13-1dc2-4f2d-9f7d-f547269a7266"),
        discord_id=discord_user_id_type("324364692547960842"),
    ),
    UserData(
        name="Jordan",
        role="Education Director",
        notion_id=notion_user_id_type("f8516599-8b82-43b5-a0a0-e7df94384912"),
        discord_id=discord_user_id_type("1254032275021238337"),
    ),
    UserData(
        name="Mark Sesuraj",
        role="Education Officer",
        notion_id=notion_user_id_type("c36b1a8d-9980-4c9c-8bf0-fd158c6144ab"),
        discord_id=discord_user_id_type("695893808595992626"),
    ),
    UserData(
        name="Prathiksha Ashok",
        role="HR Officer",
        notion_id=notion_user_id_type("0ac8066e-1874-4ef7-aac6-46ec64ab5416"),
        discord_id=discord_user_id_type("524406524567748657"),
    ),
    UserData(
        name="Sarah Abusah",
        role="Industry Director",
        notion_id=notion_user_id_type("f2103615-a0b5-46bb-b167-3ffefebb93e1"),
        discord_id=discord_user_id_type("1269646744690495638"),
    ),
    UserData(
        name="Wan Azlan",
        role="Marketing Officer",
        notion_id=notion_user_id_type("0dcaab49-891e-4e62-bc14-23ddf68c4baa"),
        discord_id=discord_user_id_type("225290307732897792"),
    ),
    UserData(
        name="Ojas",
        role="HR Officer",
        notion_id=notion_user_id_type("1d575660-d4db-48dc-bbc8-87cc8bd4ec3d"),
        discord_id=discord_user_id_type("226677092530651153"),
    ),
    UserData(
        name="Stephanie Doan",
        role="Marketing Officer",
        notion_id=notion_user_id_type("dcb83ab0-e798-4a07-93c3-550f00dc8f1a"),
        discord_id=discord_user_id_type("713786043584872459"),
    ),
    UserData(
        name="Jiacheng Zheng",
        role="Events Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-8172-9c64-0002867fd2c9"),
        discord_id=discord_user_id_type("528328814632370188"),
    ),
    UserData(
        name="Harshit Badam",
        role="Industry Officer",
        notion_id=notion_user_id_type("dc00fced-7146-4c0e-aefe-c74d939bc7b8"),
        discord_id=discord_user_id_type("432456147358842881"),
    ),
    UserData(
        name="Shawn Kim",
        role="Treasurer",
        notion_id=notion_user_id_type("1a2f8f56-d93a-4174-9ae3-426cb5614630"),
        discord_id=discord_user_id_type("1257175546039767153"),
    ),
    UserData(
        name="Divyansh ",
        role="Projects Officer",
        notion_id=notion_user_id_type("0c79bde0-3dee-4bf6-b6da-e6080c59cd8e"),
        discord_id=discord_user_id_type("708340274933268501"),
    ),
    UserData(
        name="Paige Nguyen",
        role="Industry Officer",
        notion_id=notion_user_id_type("117d872b-594c-81ee-b390-00027f46882c"),
        discord_id=discord_user_id_type("1292544598362816552"),
    ),
    UserData(
        name="Gurshan Nanda",
        role="Industry Officer",
        notion_id=notion_user_id_type("117d872b-594c-8100-8d62-0002223c005d"),
        discord_id=discord_user_id_type("1008827617283153940"),
    ),
    UserData(
        name="Dharani Baskaran",
        role="Industry Officer",
        notion_id=notion_user_id_type("117d872b-594c-81cc-95db-00029eda628a"),
        discord_id=discord_user_id_type("803068997930057768"),
    ),
    UserData(
        name="Andy Li",
        role="Industry Officer",
        notion_id=notion_user_id_type("117d872b-594c-814b-8bcd-0002bec43618"),
        discord_id=discord_user_id_type("1263063218977505283"),
    ),
    UserData(
        name="Terry Yu",
        role="Marketing Officer",
        notion_id=notion_user_id_type("51518819-39c6-49b8-b9f9-fb56b4e916d7"),
        discord_id=discord_user_id_type("583948585352298497"),
    ),
    UserData(
        name="Eric",
        role="Marketing Officer",
        notion_id=notion_user_id_type("bcb8ffb2-be38-4d92-8a68-43f21b12c209"),
        discord_id=discord_user_id_type("583630629531418684"),
    ),
    UserData(
        name="bike pham",
        role="Education Officer",
        notion_id=notion_user_id_type("fbc90953-4abf-4d56-80db-0c9df043bebe"),
        discord_id=discord_user_id_type("741125117333209288"),
    ),
    UserData(
        name="jake paul",
        role="Events Director",
        notion_id=notion_user_id_type("91fbb869-72b6-4e39-8905-bd626af0597e"),
        discord_id=discord_user_id_type("435734883462283264"),
    ),
    UserData(
        name="Aditya Yadav",
        role="Education Officer",
        notion_id=notion_user_id_type("47a28de2-00dd-4822-b73e-b19506df9bd8"),
        discord_id=discord_user_id_type("545364033008566278"),
    ),
    UserData(
        name="Mohand Mender",
        role="Undergraduate Rep",
        notion_id=notion_user_id_type("7bb29edc-bfcd-4ecd-bb2e-dab992a9ae81"),
        discord_id=discord_user_id_type("556696989048504350"),
    ),
    UserData(
        name="Irene",
        role="IT Officer",
        notion_id=notion_user_id_type("144d872b-594c-819d-a5ac-0002b701ee00"),
        discord_id=discord_user_id_type("569831538078777354"),
    ),
    UserData(
        name="Abhin Rustagi",
        role="IT Officer",
        notion_id=notion_user_id_type("144d872b-594c-81c7-b610-00029b02bba9"),
        discord_id=discord_user_id_type("974714458779832320"),
    ),
    UserData(
        name="Animesh",
        role="IT Officer",
        notion_id=notion_user_id_type("144d872b-594c-813b-a24b-000246c48adb"),
        discord_id=discord_user_id_type("449806786791211008"),
    ),
    UserData(
        name="Ishan Deshpande",
        role="IT Officer",
        notion_id=notion_user_id_type("144d872b-594c-812d-8589-0002838bda39"),
        discord_id=discord_user_id_type("572691462085541908"),
    ),
    UserData(
        name="Tanat Chanwangsa",
        role="IT Officer",
        notion_id=notion_user_id_type("147d872b-594c-81ae-9f01-0002a25dc7c7"),
        discord_id=discord_user_id_type("262140744796602368"),
    ),
    UserData(
        name="Henry Routson",
        role="AI Officer",
        notion_id=notion_user_id_type("149d872b-594c-8184-ba71-00021997dcb9"),
        discord_id=discord_user_id_type("872718183692402688"),
    ),
    UserData(
        name="Pranav Jayanty",
        role="AI Officer",
        notion_id=notion_user_id_type("c005948c-9115-4a4d-b3c2-78286fa75fdb"),
        discord_id=discord_user_id_type("373796704450772992"),
    ),
    UserData(
        name="Pavan Dev",
        role="Events Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-8100-aead-00026f26d36d"),
        discord_id=discord_user_id_type("489420534019391488"),
    ),
    UserData(
        name="Lachlan Chue",
        role="IT Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-81a3-b7d2-0002e41f8537"),
        discord_id=discord_user_id_type("313177325879558145"),
    ),
    UserData(
        name="Addie Nguyen",
        role="Marketing Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-813f-88ba-00022d2ea8d8"),
        discord_id=discord_user_id_type("810545230632976385"),
    ),
    UserData(
        name="Anthea Lee",
        role="Events Officer",
        notion_id=notion_user_id_type("1bad872b-594c-81bb-95f1-00025ff97f57"),
        discord_id=discord_user_id_type("768799326141939764"),
    ),
    UserData(
        name="Dhruv Verma",
        role="IT Officer",
        notion_id=notion_user_id_type("1bad872b-594c-8110-91e2-0002c091f384"),
        discord_id=discord_user_id_type("808488202163322881"),
    ),
    UserData(
        name="Frank Ngo",
        role="Education Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-815a-a001-000245072ba6"),
        discord_id=discord_user_id_type("447293645981351946"),
    ),
    UserData(
        name="Carmen Wong",
        role="Marketing Officer",
        notion_id=notion_user_id_type("1bad872b-594c-817c-aa7b-000212ba08a1"),
        discord_id=discord_user_id_type("1350954484913799211"),
    ),
    UserData(
        name="Zim",
        role="IT Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-8159-9858-000210dbca44"),
        discord_id=discord_user_id_type("655681641834086431"),
    ),
    UserData(
        name="Eric He",
        role="Events Officer",
        notion_id=notion_user_id_type("1bad872b-594c-8129-89c2-0002ee1ba61e"),
        discord_id=discord_user_id_type("994501536250069013"),
    ),
    UserData(
        name="Damien Trinh",
        role="Events Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-81b7-bb3d-00020c61fc37"),
        discord_id=discord_user_id_type("386352490150363136"),
    ),
    UserData(
        name="Keith Howen",
        role="Education Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-815b-b5f2-0002f50ecfe5"),
        discord_id=discord_user_id_type("688543302429311087"),
    ),
    UserData(
        name="Chi Nguyen",
        role="Marketing Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-81c6-9711-00027493224c"),
        discord_id=discord_user_id_type("1053356459565514863"),
    ),
    UserData(
        name="Eddie Li",
        role="IT Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-818b-8142-00022dae03c4"),
        discord_id=discord_user_id_type("1340308441645842553"),
    ),
    UserData(
        name="Rudra Tiwari",
        role="Marketing Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-8167-b7bb-000231b0eaa5"),
        discord_id=discord_user_id_type("1038316180991131728"),
    ),
    UserData(
        name="Stanley",
        role="Education Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-8198-b16d-00029b7b516a"),
        discord_id=discord_user_id_type("424310464839942174"),
    ),
    UserData(
        name="Yiwen Zhang",
        role="AI Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-8123-a9c8-0002e6ee833b"),
        discord_id=discord_user_id_type("774065995508744232"),
    ),
    UserData(
        name="Shayomi",
        role="AI Officer",  # TODO
        notion_id=notion_user_id_type("1bbd872b-594c-816b-b37d-000274bbfbe2"),
        discord_id=discord_user_id_type("744518516350386298"),
    ),
    UserData(
        name="Antoine",
        role="AI Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-81f5-bc03-0002a7229ca6"),
        discord_id=discord_user_id_type("1195065884713156728"),
    ),
    UserData(
        name="lorraine sanares",
        role="AI Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-816f-b62c-000253e00baa"),
        discord_id=discord_user_id_type("1215094966846758952"),
    ),
    UserData(
        name="Alina",
        role="AI Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-81e9-a745-000238c87ef8"),
        discord_id=discord_user_id_type("1283302616759275581"),
    ),
    UserData(
        name="Liao Ziang",
        role="AI Officer",
        notion_id=notion_user_id_type("1bbd872b-594c-8160-8126-00029d7b0a08"),
        discord_id=discord_user_id_type("946858733756117094"),
    ),
]


DISCORD_TO_NOTION_USER_MAP: dict[discord_user_id_type, UserData] = {
    user.discord_id: user for user in USER_LIST
}
NOTION_TO_DISCORD_USER_MAP: dict[notion_user_id_type, UserData] = {
    user.notion_id: user for user in USER_LIST
}


# wrappers for type safety


def get_user_from_discord_id(discord_id: discord_user_id_type) -> UserData | None:
    return DISCORD_TO_NOTION_USER_MAP.get(discord_id)


def get_user_from_notion_id(notion_id: notion_user_id_type) -> UserData | None:
    return NOTION_TO_DISCORD_USER_MAP.get(notion_id)


def notion_to_discord_user_map(
    notion_id: notion_user_id_type,
) -> discord_user_id_type | None:
    user_data: UserData | None = get_user_from_notion_id(notion_id)
    if user_data is None:
        return None
    return user_data.discord_id


def discord_to_notion_user_map(
    discord_id: discord_user_id_type,
) -> notion_user_id_type | None:
    user_data: UserData | None = get_user_from_discord_id(discord_id)
    if user_data is None:
        return None
    return user_data.notion_id


# testing

for user in USER_LIST:
    assert notion_to_discord_user_map(user.notion_id) == user.discord_id
    assert discord_to_notion_user_map(user.discord_id) == user.notion_id


print("Done testing")
