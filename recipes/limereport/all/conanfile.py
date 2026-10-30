import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import copy, get, replace_in_file
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LimereportConan(ConanFile):
    name = "limereport"
    description = "Report generator for Qt Framework"
    homepage = "https://limereport.ru"
    topics = ("limereport", "pdf", "report","qt")
    license = "LGPL-3.0", "GPL-3.0"
    url = "https://github.com/conan-io/conan-center-index"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_zint": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_zint": False,
    }

    @property
    def _qt_version_major(self):
        return Version(self.dependencies["qt"].ref.version).major

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # QString included in Irglobal.h and Limereport expects be running Qt on customer side
        self.requires("qt/[>=5.15 <7]", transitive_headers=True, transitive_libs=True,
                      options={"qtdeclarative": True, "qtsvg": True, "qttools": True})
        if self.options.with_zint:
            self.requires("zint/2.16.0")

    def validate(self):
        check_min_cppstd(self, 17)
        qt = self.dependencies["qt"]
        if not all([qt.options.qtdeclarative, qt.options.qtsvg, qt.options.qttools]):
            raise ConanInvalidConfiguration("Requires -o='qt/*:qtdeclarative=True' -o='qt/*:qtsvg=True' -o='qt/*:qttools=True'")
        if self.options.with_zint and not self.dependencies["zint"].options.with_qt:
            raise ConanInvalidConfiguration("Option with_zint=True requires -o 'zint/*:with_qt=True'")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], destination=self.source_folder, strip_root=True)
        self._patch_sources()

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["LIMEREPORT_STATIC"] = not self.options.shared
        tc.cache_variables["HAVE_UI_LOADER"] = True
        tc.cache_variables["USE_QT6"] = self._qt_version_major == 6
        tc.cache_variables["ENABLE_ZINT"] = self.options.with_zint
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def _patch_sources(self):
        # Avoid using vendozied zint
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(self, cmakelists, "add_subdirectory(3rdparty)", "")
        replace_in_file(self, cmakelists, "set(CMAKE_CXX_STANDARD 17)", "")
        # The QZint target was defined by the vendored zint, use the one from the zint recipe instead
        replace_in_file(self, cmakelists, "target_link_libraries( ${PROJECT_NAME} PRIVATE QZint)",
                        "find_package(Zint REQUIRED CONFIG)\n    target_link_libraries( ${PROJECT_NAME} PRIVATE Zint::QZint)")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = [f"limereport-qt{self._qt_version_major}"]
        self.cpp_info.requires = ["qt::qtCore", "qt::qtWidgets", "qt::qtQml", "qt::qtXml", "qt::qtSql",
                                   "qt::qtPrintSupport", "qt::qtSvg", "qt::qtUiTools"]
        if self.options.with_zint:
            self.cpp_info.requires.append("zint::zint")
        if self.options.shared:
            self.cpp_info.defines.append("LIMEREPORT_IMPORTS")
