"""Scenes, styles and the prompt sent to the image-editing model."""

from apps.catalog.models import ProductType

# value -> (label, prompt fragment)
SCENES: dict[str, tuple[str, str]] = {
    "city_night": ("City at night", "on a wet city street at night, neon reflections on the asphalt"),
    "mountain_road": ("Mountain road", "on a winding mountain road with pine trees, golden hour light"),
    "race_track": ("Race track", "on a racing circuit pit straight, bright overcast daylight"),
    "coastal_road": ("Coastal road", "on a coastal road above the sea, clear sunny afternoon"),
    "studio": ("Studio", "in a clean photo studio with a seamless grey backdrop and soft lighting"),
    "keep_background": ("Keep my background", "in the original location of the photo, background unchanged"),
}

STYLES: dict[str, tuple[str, str]] = {
    "photo": ("Photorealistic", "Photorealistic, natural colours, sharp focus."),
    "cinematic": ("Cinematic", "Cinematic colour grading, shallow depth of field, dramatic light."),
    "magazine": ("Car magazine", "Professional automotive magazine shoot, polished and glossy."),
}

WHEEL_TYPES = (ProductType.WHEEL, ProductType.SET)
# Named choice lists for the OpenAPI schema (see ENUM_NAME_OVERRIDES).
SCENE_CHOICES = [(value, label) for value, (label, _) in SCENES.items()]
STYLE_CHOICES = [(value, label) for value, (label, _) in STYLES.items()]


def options(choices: dict[str, tuple[str, str]]) -> list[dict[str, str]]:
    return [{"value": value, "label": label} for value, (label, _) in choices.items()]


def describe_wheel(variant) -> str:
    if variant is None:
        return "stylish aftermarket alloy wheels that suit the car"
    product = variant.product
    parts = [
        f"{variant.diameter_in}-inch" if variant.diameter_in else "",
        variant.get_finish_display().lower() if variant.finish else "",
        f"{product.get_style_display().lower()} design" if product.style else "",
        "alloy wheels",
    ]
    return f"{' '.join(p for p in parts if p)} ({product.brand.name} {product.name})"


def build_prompt(generation) -> str:
    scene = SCENES.get(generation.scene, SCENES["keep_background"])[1]
    style = STYLES.get(generation.style, STYLES["photo"])[1]
    return (
        f"Replace only the wheels of the car in this photo with {describe_wheel(generation.variant)}. "
        "Keep the car's body, colour, shape, camera angle and tyres unchanged and keep the wheels "
        f"correctly sized for the wheel arches. Show the car {scene}. {style} "
        "Do not add text, logos or people; blur or omit any licence plate."
    )
