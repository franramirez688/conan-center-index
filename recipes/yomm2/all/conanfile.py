import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.files import get, rm, rmdir, copy
from conan.tools.scm import Version
from conans.errors import ConanInvalidConfiguration

required_conan_version = ">=1.53.0"


class yomm2Recipe(ConanFile):
    name = "yomm2"
    package_type = "library"  # if static, it's a header-only one
    # Optional metadata
    license = "BSL-1.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/jll63/yomm2"
    description = "Fast, orthogonal, open multi-methods. Solve the Expression Problem in C++17"
    topics = ("multi-methods", "library", "header-only", "expressions", "c++17")
    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True
    }

    @property
    def _min_cppstd(self):
        return 17

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "8",
            "clang": "5",
            "apple-clang": "12",
            "msvc": "192"
        }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
        if minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support."
            )

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.20 <4]")

    def requirements(self):
        # Upstream requires Boost 1.74
        # Using more modern Boost version to avoid issues like the one commented here:
        # - https://github.com/conan-io/conan/issues/15977#issuecomment-2098003085
        self.requires("boost/1.85.0", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["YOMM2_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["YOMM2_ENABLE_TESTS"] = "OFF"
        tc.variables["YOMM2_SHARED"] = self.options.shared
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        if self.options.shared:
            rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        else:  # header-only one
            rmdir(self, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "YOMM2")
        self.cpp_info.set_property("cmake_target_name", "YOMM2::yomm2")
        if self.options.shared:
            self.cpp_info.libs = ["yomm2"]
        else:  # header-only one
            self.cpp_info.bindirs = []
            self.cpp_info.libdirs = []
