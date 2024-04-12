from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get, rmdir, rename
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version
from conan.tools.microsoft import is_msvc
from conan.tools.env import VirtualBuildEnv
import os


required_conan_version = ">=1.64.0 <2 || >=2.2.0"


class ThorvgConan(ConanFile):
    name = "thorvg"
    description = "ThorVG is a platform-independent portable library that allows for drawing vector-based scenes and animations."
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/thorvg/thorvg"
    topics = ("svg", "animation", "tvg")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_engines": ['sw', 'gl_beta', 'wg_beta'],
        "with_loaders": [False, 'tvg', 'svg', 'png', 'jpg', 'lottie', 'ttf', 'webp', 'all'],
        "with_savers": [False, 'tvg', 'gif', 'all'],
        "with_bindings": [False, 'capi', 'wasm_beta'],
        "with_tools": [False, 'svg2tvg', 'svg2png', 'lottie2gif', 'all'],
        "with_threads": [True, False],
        "with_vector": [True, False],
        "with_examples": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_engines": 'sw',
        "with_loaders": 'all',
        "with_savers": False,
        "with_bindings": 'capi',
        "with_tools": False,
        "with_threads": True,
        "with_vector": False,
        "with_examples": False
    }
    # See more here: https://github.com/thorvg/thorvg/blob/main/meson_options.txt
    options_description = {
        "engines": "Enable Rasterizer Engine in thorvg",
        "loaders": "Enable File Loaders in thorvg",
        "savers": "Enable File Savers in thorvg",
        "threads": "Enable the multi-threading task scheduler in thorvg",
        "vector": "Enable CPU Vectorization(SIMD) in thorvg",
        "bindings": "Enable API bindings",
        "tools": "Enable building thorvg tools",
        "examples": "Enable building examples",
    }

    @property
    def _min_cppstd(self):
        return 14

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "6",
            "clang": "5",
            "apple-clang": "10",
            "Visual Studio": "15",
            "msvc": "191",
        }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
        if minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support."
            )

    def build_requirements(self):
        self.tool_requires("meson/1.4.0")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/2.1.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if is_msvc(self):
            tc = MesonToolchain(self, backend="vs")
        else:
            tc = MesonToolchain(self)
        is_debug = self.settings.get_safe("build_type") == "Debug"
        tc.project_options.update({
            "static": not bool(self.options.shared),
            "engines": str(self.options.with_engines),
            "loaders": str(self.options.with_loaders) if self.options.with_loaders else '',
            "savers": str(self.options.with_savers) if self.options.with_savers else '',
            "bindings": str(self.options.with_bindings) if self.options.with_bindings else '',
            "tools": str(self.options.with_tools )if self.options.with_tools else '',
            "threads": bool(self.options.with_threads),
            "vector": bool(self.options.with_vector),
            "examples": bool(self.options.with_examples),
            "tests": False,
            "log": is_debug
        })
        tc.generate()
        tc = PkgConfigDeps(self)
        tc.generate()
        venv = VirtualBuildEnv(self)
        venv.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

        if is_msvc(self) and not self.options.shared:
            rename(self, os.path.join(self.package_folder, "lib", "libthorvg.a"), os.path.join(self.package_folder, "lib", "thorvg.lib"))

    def package_info(self):
        self.cpp_info.libs = ["thorvg"]

        self.cpp_info.set_property("pkg_config_name", "libthorvg")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["pthread"])
