import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, export_conandata_patches, get, copy, rmdir, rm,
                               replace_in_file)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version
from conan.tools.system import package_manager

required_conan_version = ">=2.0"

# --- Option definitions (single source of truth for components and dependencies) ---

PCL_CORE_COMPONENTS = [
    "2d", "features", "filters", "geometry", "io", "kdtree", "keypoints", "ml",
    "octree", "outofcore", "people", "recognition", "registration", "sample_consensus",
    "search", "segmentation", "simulation", "stereo", "surface", "tracking", "visualization",
]
PCL_GPU_COMPONENTS = [
    "cuda_common", "cuda_features", "cuda_io", "cuda_sample_consensus", "cuda_segmentation",
    "gpu_containers", "gpu_features", "gpu_kinfu", "gpu_kinfu_large_scale", "gpu_octree",
    "gpu_people", "gpu_segmentation", "gpu_surface", "gpu_tracking", "gpu_utils",
]
PCL_EXTRA_COMPONENTS = ["apps", "tools"]
PCL_WITH_DEPS = [
    "cuda", "flann", "libusb", "opencv", "opengl", "openmp", "pcap", "png", "qhull", "qt", "vtk",
]
PCL_ALWAYS_ENABLED_DEPS = frozenset({"boost", "eigen", "zlib"})
PCL_HEADER_ONLY_COMPONENTS = frozenset({"2d", "cuda_common", "geometry"})
# Find*.cmake modules to remove so Conan-provided configs are used
PCL_FIND_MODULES_TO_REMOVE = ("Eigen", "FLANN", "GLEW", "Pcap", "Qhull", "libusb")
# MSVC runtime DLLs to remove from package bin folder
PCL_MSVC_DLL_PATTERNS = ("concrt*.dll", "msvcp*.dll", "vcruntime*.dll")

# Options that default to True (all others default to False)
PCL_DEFAULT_TRUE = frozenset({
    "2d", "features", "filters", "geometry", "io", "kdtree", "keypoints", "ml", "octree",
    "recognition", "registration", "sample_consensus", "search", "segmentation", "stereo",
    "surface", "tracking",
    "with_flann", "with_libusb", "with_opencv", "with_opengl", "with_pcap", "with_png",
    "with_qhull", "with_qt",
    "precompile_only_core_point_types", "use_sse", "use_avx",
})

# Component -> list of required external dependency names (from CMakeLists.txt)
EXTERNAL_DEPS = {
    "common": ["boost", "eigen"],
    "cuda_common": ["cuda"],
    "cuda_features": ["cuda"],
    "cuda_io": ["cuda", "openni"],
    "cuda_sample_consensus": ["cuda"],
    "cuda_segmentation": ["cuda"],
    "gpu_containers": ["cuda"],
    "gpu_features": ["cuda"],
    "gpu_kinfu": ["cuda"],
    "gpu_kinfu_large_scale": ["cuda"],
    "gpu_octree": ["cuda"],
    "gpu_people": ["cuda"],
    "gpu_segmentation": ["cuda"],
    "gpu_surface": ["cuda"],
    "gpu_tracking": ["cuda"],
    "gpu_utils": ["cuda"],
    "io": ["zlib"],
    "people": ["vtk"],
    "surface": ["zlib"],
    "visualization": ["vtk"],
}

# Component -> list of optional external dependency names
EXTERNAL_OPTIONAL_DEPS = {
    "2d": ["vtk"],
    "io": ["davidsdk", "dssdk", "ensenso", "fzapi", "libusb", "openni", "openni2", "pcap", "png", "rssdk", "rssdk2", "vtk"],
    "kdtree": ["flann"],
    "people": ["openni"],
    "recognition": ["metslib"],
    "search": ["flann"],
    "simulation": ["opengl"],
    "surface": ["qhull", "vtk"],
    "visualization": ["davidsdk", "dssdk", "ensenso", "opengl", "openni", "openni2", "qvtk", "rssdk"],
    "apps": ["cuda", "libusb", "opengl", "openni", "png", "qhull", "qt", "qvtk", "vtk"],
    "tools": ["cuda", "davidsdk", "dssdk", "ensenso", "opencv", "opengl", "openni", "openni2", "qhull", "rssdk", "vtk"],
}

# External dep name -> Conan cmake target(s). Opengl glu target is OS-dependent, handled in package_info.
EXTERNAL_DEP_TARGETS = {
    "boost": ["boost::boost"],
    "cuda": [],
    "davidsdk": [],
    "dssdk": [],
    "eigen": ["eigen::eigen"],
    "ensenso": [],
    "flann": ["flann::flann"],
    "fzapi": [],
    "libusb": ["libusb::libusb"],
    "metslib": [],
    "opencv": ["opencv::opencv"],
    "openni": [],
    "openni2": [],
    "pcap": ["libpcap::libpcap"],
    "png": ["libpng::libpng"],
    "qhull": ["qhull::qhull"],
    "qt": ["qt::qt"],
    "qvtk": [],
    "rssdk": [],
    "rssdk2": [],
    "vtk": [],
    "zlib": ["zlib::zlib"],
}

# Component -> list of internal PCL component names it depends on
INTERNAL_DEPS = {
    "2d": ["common", "filters"],
    "common": [],
    "cuda_common": [],
    "cuda_features": ["common", "cuda_common", "io"],
    "cuda_io": ["common", "cuda_common", "io"],
    "cuda_sample_consensus": ["common", "cuda_common", "io"],
    "cuda_segmentation": ["common", "cuda_common", "io"],
    "features": ["2d", "common", "filters", "kdtree", "octree", "search"],
    "filters": ["common", "kdtree", "octree", "sample_consensus", "search"],
    "geometry": ["common"],
    "gpu_containers": ["common"],
    "gpu_features": ["common", "geometry", "gpu_containers", "gpu_octree", "gpu_utils"],
    "gpu_kinfu": ["common", "geometry", "gpu_containers", "io", "search"],
    "gpu_kinfu_large_scale": ["common", "features", "filters", "geometry", "gpu_containers",
                              "gpu_utils", "io", "kdtree", "octree", "search", "surface"],
    "gpu_octree": ["common", "gpu_containers", "gpu_utils"],
    "gpu_people": ["common", "features", "filters", "geometry", "gpu_containers",
                   "gpu_utils", "io", "kdtree", "octree", "search", "segmentation",
                   "surface", "visualization"],
    "gpu_segmentation": ["common", "gpu_containers", "gpu_octree", "gpu_utils"],
    "gpu_surface": ["common", "geometry", "gpu_containers", "gpu_utils"],
    "gpu_tracking": ["common", "filters", "gpu_containers", "gpu_octree",
                     "gpu_utils", "kdtree", "octree", "search", "tracking"],
    "gpu_utils": ["common", "gpu_containers"],
    "io": ["common", "octree"],
    "kdtree": ["common"],
    "keypoints": ["common", "features", "filters", "kdtree", "octree", "search"],
    "ml": ["common"],
    "octree": ["common"],
    "outofcore": ["common", "filters", "io", "octree", "visualization"],
    "people": ["common", "filters", "geometry", "io", "kdtree", "octree",
               "sample_consensus", "search", "segmentation", "visualization"],
    "recognition": ["common", "features", "filters", "io", "kdtree", "ml",
                   "octree", "registration", "sample_consensus", "search"],
    "registration": ["common", "features", "filters", "kdtree", "octree",
                     "sample_consensus", "search"],
    "sample_consensus": ["common", "search"],
    "search": ["common", "kdtree", "octree"],
    "segmentation": ["common", "features", "filters", "geometry", "kdtree",
                     "ml", "octree", "sample_consensus", "search"],
    "simulation": ["common", "features", "filters", "geometry", "io",
                   "kdtree", "octree", "search", "surface", "visualization"],
    "stereo": ["common", "io"],
    "surface": ["common", "kdtree", "octree", "search"],
    "tracking": ["common", "filters", "kdtree", "octree", "search"],
    "visualization": ["common", "geometry", "io", "kdtree", "octree", "search"],
}

# Apps/tools -> list of internal components they need
INTERNAL_OPTIONAL_DEPS = {
    "apps": ["2d", "common", "cuda_common", "cuda_features", "cuda_io",
             "cuda_sample_consensus", "cuda_segmentation", "features", "filters",
             "geometry", "io", "kdtree", "keypoints", "ml", "octree", "recognition",
             "registration", "sample_consensus", "search", "segmentation", "stereo",
             "surface", "tracking", "visualization"],
    "tools": ["features", "filters", "geometry", "gpu_kinfu", "gpu_kinfu_large_scale",
              "io", "kdtree", "keypoints", "ml", "octree", "recognition", "registration",
              "sample_consensus", "search", "segmentation", "surface", "visualization"],
}

# Component -> extra library names (e.g. pcl_io_ply)
EXTRA_LIBS = {"io": ["pcl_io_ply"]}

COMPILERS_MINIMUM_VERSION = {"gcc": "7", "clang": "7", "apple-clang": "10", "msvc": "191", "Visual Studio": "15"}


def _pcl_options_dict():
    """Build options dict from component and dependency lists."""
    opts = {"shared": [True, False], "fPIC": [True, False]}
    for c in PCL_CORE_COMPONENTS + PCL_GPU_COMPONENTS + PCL_EXTRA_COMPONENTS:
        opts[c] = [True, False]
    for d in PCL_WITH_DEPS:
        opts[f"with_{d}"] = [True, False]
    opts["precompile_only_core_point_types"] = [True, False]
    opts["add_build_type_postfix"] = [True, False]
    opts["use_sse"] = [True, False]
    opts["use_avx"] = [True, False]
    return opts


def _pcl_default_options():
    """Build default_options from PCL_DEFAULT_TRUE; rest are False."""
    opts = _pcl_options_dict()
    defaults = {opt: (opt in PCL_DEFAULT_TRUE) for opt in opts}
    defaults["shared"] = False
    defaults["fPIC"] = True
    defaults["add_build_type_postfix"] = False
    defaults["precompile_only_core_point_types"] = True
    defaults["use_sse"] = True
    defaults["use_avx"] = True
    return defaults


class PclConan(ConanFile):
    """Conan recipe for Point Cloud Library (PCL)."""

    name = "pcl"
    description = (
        "The Point Cloud Library (PCL) is a standalone, large-scale, "
        "open project for 2D/3D image and point cloud processing."
    )
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/PointCloudLibrary/pcl"
    topics = ("computer vision", "point cloud", "pointcloud", "3d", "pcd", "ply", "stl", "ifs", "vtk")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = _pcl_options_dict()
    default_options = _pcl_default_options()
    short_paths = True

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.arch not in ["x86", "x86_64"]:
            del self.options.use_sse
            del self.options.use_avx

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def system_requirements(self):
        enabled = {c for c in INTERNAL_DEPS if self.options.get_safe(c)} | {"common"}
        used_ext = set()
        for c in enabled:
            used_ext.update(EXTERNAL_DEPS.get(c, []))
            used_ext.update(EXTERNAL_OPTIONAL_DEPS.get(c, []))
        if "vtk" in used_ext and (self.options.get_safe("with_vtk") or "vtk" in PCL_ALWAYS_ENABLED_DEPS):
            # TODO: add vtk/system package? https://repology.org/project/vtk/versions
            package_manager.Apt(self).install(["libvtk9-dev"], update=True, check=True)
            package_manager.Dnf(self).install(["vtk-devel"], update=True, check=True)
            package_manager.Yum(self).install(["vtk-devel"], update=True, check=True)
            package_manager.PacMan(self).install(["vtk"], update=True, check=True)
            package_manager.Zypper(self).install(["vtk"], update=True, check=True)
            package_manager.Pkg(self).install(["vtk9"], update=True, check=True)
            package_manager.Brew(self).install(["vtk"], update=True, check=True)
            if self.settings.os == "Windows":
                self.output.warning("VTK must be installed manually on Windows.")

    def requirements(self):
        enabled = {c for c in INTERNAL_DEPS if self.options.get_safe(c)} | {"common"}
        used_ext = set()
        for c in enabled:
            used_ext.update(EXTERNAL_DEPS.get(c, []))
            used_ext.update(EXTERNAL_OPTIONAL_DEPS.get(c, []))

        self.requires("boost/1.83.0", transitive_headers=True)
        self.requires("eigen/[>=3.4.0 <4]", transitive_headers=True)
        if "flann" in used_ext and (self.options.get_safe("with_flann") or "flann" in PCL_ALWAYS_ENABLED_DEPS):
            self.requires("flann/1.9.2", transitive_headers=True)
        if "png" in used_ext and (self.options.get_safe("with_png") or "png" in PCL_ALWAYS_ENABLED_DEPS):
            self.requires("libpng/[>=1.6 <2]")
        if "qhull" in used_ext and (self.options.get_safe("with_qhull") or "qhull" in PCL_ALWAYS_ENABLED_DEPS):
            self.requires("qhull/8.0.2", transitive_headers=True)
        if "qt" in used_ext and (self.options.get_safe("with_qt") or "qt" in PCL_ALWAYS_ENABLED_DEPS):
            self.requires("qt/[>=6.6 <7]")
        if "libusb" in used_ext and (self.options.get_safe("with_libusb") or "libusb" in PCL_ALWAYS_ENABLED_DEPS):
            self.requires("libusb/1.0.26", transitive_headers=True)
        if "pcap" in used_ext and (self.options.get_safe("with_pcap") or "pcap" in PCL_ALWAYS_ENABLED_DEPS):
            self.requires("libpcap/1.10.4")
        if "opengl" in used_ext and (self.options.get_safe("with_opengl") or "opengl" in PCL_ALWAYS_ENABLED_DEPS):
            self.requires("opengl/system", transitive_headers=True)
            self.requires("freeglut/3.4.0", transitive_headers=True)
            self.requires("glew/2.2.0", transitive_headers=True)
            if is_apple_os(self) or self.settings.os == "Windows":
                self.requires("glu/system", transitive_headers=True)
            else:
                self.requires("mesa-glu/9.0.3", transitive_headers=True)
        if "opencv" in used_ext and (self.options.get_safe("with_opencv") or "opencv" in PCL_ALWAYS_ENABLED_DEPS):
            self.requires("opencv/[>=4.8.1 <5]", transitive_headers=True)
        if "zlib" in used_ext and (self.options.get_safe("with_zlib") or "zlib" in PCL_ALWAYS_ENABLED_DEPS):
            self.requires("zlib/[>=1.2.11 <2]")
        # TODO: vtk, openni, openni2, ensenso, davidsdk, dssdk, rssdk, metslib, openmp, opennurbs, poisson4

    def package_id(self):
        enabled = {c for c in INTERNAL_DEPS if self.info.options.get_safe(c)} | {"common"}
        used_ext = set()
        for c in enabled:
            used_ext.update(EXTERNAL_DEPS.get(c, []))
            used_ext.update(EXTERNAL_OPTIONAL_DEPS.get(c, []))
        for opt, value in self.info.options.items():
            if opt.startswith("with_") and opt.split("_", 1)[1] not in used_ext:
                setattr(self.info.options, opt, False)

    def validate(self):
        enabled = {c for c in INTERNAL_DEPS if self.options.get_safe(c)} | {"common"}

        for component in sorted(enabled):
            for dep in EXTERNAL_DEPS.get(component, []):
                if not (self.options.get_safe(f"with_{dep}") or dep in PCL_ALWAYS_ENABLED_DEPS):
                    raise ConanInvalidConfiguration(
                        f"'with_{dep}=True' is required when '{component}' is enabled."
                    )
            for dep in INTERNAL_DEPS[component]:
                if dep not in enabled:
                    raise ConanInvalidConfiguration(
                        f"'{dep}=True' is required when '{component}' is enabled."
                    )

        if self.settings.compiler.cppstd:
            check_min_cppstd(self, 17)
        min_ver = COMPILERS_MINIMUM_VERSION.get(str(self.settings.compiler), False)
        if min_ver and Version(self.settings.compiler.version) < min_ver:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++17, which your compiler does not support."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        cmake_modules = os.path.join(self.source_folder, "cmake", "Modules")
        for mod in PCL_FIND_MODULES_TO_REMOVE:
            find_path = os.path.join(cmake_modules, f"Find{mod}.cmake")
            if os.path.exists(find_path):
                os.remove(find_path)
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(self, cmake_lists,
                        'if(PCL_ENABLE_AVX AND "${CMAKE_CXX_FLAGS}" STREQUAL "${CMAKE_CXX_FLAGS_DEFAULT}")',
                        'if(PCL_ENABLE_AVX)')
        replace_in_file(self, cmake_lists,
                        'if(PCL_ENABLE_SSE AND "${CMAKE_CXX_FLAGS}" STREQUAL "${CMAKE_CXX_FLAGS_DEFAULT}")',
                        'if(PCL_ENABLE_SSE)')
        replace_in_file(self, cmake_lists,
                        'if("${CMAKE_CXX_FLAGS}" STREQUAL "${CMAKE_CXX_FLAGS_DEFAULT}")',
                        'if(1)')
        replace_in_file(self, cmake_lists,
                        'if("${CMAKE_CXX_FLAGS}" STREQUAL "")',
                        'if(1)')

    def generate(self):
        enabled = {c for c in INTERNAL_DEPS if self.options.get_safe(c)} | {"common"}
        used_ext = set()
        for c in enabled:
            used_ext.update(EXTERNAL_DEPS.get(c, []))
            used_ext.update(EXTERNAL_OPTIONAL_DEPS.get(c, []))

        tc = CMakeToolchain(self)
        tc.cache_variables["PCL_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["WITH_LIBUSB"] = "libusb" in used_ext and (self.options.get_safe("with_libusb") or "libusb" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["WITH_OPENGL"] = "opengl" in used_ext and (self.options.get_safe("with_opengl") or "opengl" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["WITH_OPENMP"] = "openmp" in used_ext and (self.options.get_safe("with_openmp") or "openmp" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["WITH_PCAP"] = "pcap" in used_ext and (self.options.get_safe("with_pcap") or "pcap" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["WITH_PNG"] = "png" in used_ext and (self.options.get_safe("with_png") or "png" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["WITH_QHULL"] = "qhull" in used_ext and (self.options.get_safe("with_qhull") or "qhull" in PCL_ALWAYS_ENABLED_DEPS)
        if "qhull" in used_ext and (self.options.get_safe("with_qhull") or "qhull" in PCL_ALWAYS_ENABLED_DEPS):
            tc.cache_variables["HAVE_QHULL"] = True
        tc.cache_variables["WITH_QT"] = "qt" in used_ext and (self.options.get_safe("with_qt") or "qt" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["WITH_VTK"] = "vtk" in used_ext and (self.options.get_safe("with_vtk") or "vtk" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["WITH_CUDA"] = "cuda" in used_ext and (self.options.get_safe("with_cuda") or "cuda" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["BUILD_CUDA"] = "cuda" in used_ext and (self.options.get_safe("with_cuda") or "cuda" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["BUILD_GPU"] = "cuda" in used_ext and (self.options.get_safe("with_cuda") or "cuda" in PCL_ALWAYS_ENABLED_DEPS)
        tc.cache_variables["WITH_SYSTEM_ZLIB"] = True
        if not is_msvc(self):
            tc.cache_variables["PCL_ONLY_CORE_POINT_TYPES"] = self.options.precompile_only_core_point_types
        tc.cache_variables["PCL_ALLOW_BOTH_SHARED_AND_STATIC_DEPENDENCIES"] = True
        tc.variables["OpenGL_GL_PREFERENCE"] = "GLVND"

        if not self.options.add_build_type_postfix:
            tc.cache_variables["CMAKE_DEBUG_POSTFIX"] = ""
            tc.cache_variables["CMAKE_RELEASE_POSTFIX"] = ""
            tc.cache_variables["CMAKE_RELWITHDEBINFO_POSTFIX"] = ""
            tc.cache_variables["CMAKE_MINSIZEREL_POSTFIX"] = ""

        tc.cache_variables["BUILD_tools"] = self.options.tools
        tc.cache_variables["BUILD_apps"] = self.options.apps
        tc.cache_variables["BUILD_examples"] = False
        enabled_list = sorted(enabled)
        disabled_list = sorted({c for c in INTERNAL_DEPS if not self.options.get_safe(c)} - {"common"})
        self.output.info("Enabled components: " + ", ".join(enabled_list))
        self.output.info("Disabled components: " + ", ".join(disabled_list))
        for comp in enabled_list:
            tc.cache_variables[f"BUILD_{comp}"] = True
        for comp in disabled_list:
            tc.cache_variables[f"BUILD_{comp}"] = False

        tc.cache_variables["PCL_ENABLE_SSE"] = self.options.get_safe("use_sse", False)
        tc.cache_variables["PCL_ENABLE_MARCHNATIVE"] = False
        tc.cache_variables["PCL_ENABLE_AVX"] = self.options.get_safe("use_avx", False)
        tc.cache_variables["HAVE_AVX2"] = self.options.get_safe("use_avx", False)
        tc.generate()

        cmake_deps = CMakeDeps(self)
        cmake_deps.set_property("eigen", "cmake_file_name", "EIGEN")
        cmake_deps.set_property("flann", "cmake_file_name", "FLANN")
        cmake_deps.set_property("flann", "cmake_target_name", "FLANN::FLANN")
        cmake_deps.set_property("libpcap", "cmake_file_name", "PCAP")
        cmake_deps.set_property("qhull", "cmake_file_name", "QHULL")
        cmake_deps.set_property("qhull", "cmake_target_name", "QHULL::QHULL")
        cmake_deps.generate()
        PkgConfigDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        for pattern in PCL_MSVC_DLL_PATTERNS:
            rm(self, pattern, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        semver = Version(self.version)
        version_suffix = f"{semver.major}.{semver.minor}"
        pcl_include_dir = os.path.join("include", f"pcl-{version_suffix}")

        enabled = {c for c in INTERNAL_DEPS if self.options.get_safe(c)} | {"common"}
        used_ext = set()
        for c in enabled:
            used_ext.update(EXTERNAL_DEPS.get(c, []))
            used_ext.update(EXTERNAL_OPTIONAL_DEPS.get(c, []))

        self.cpp_info.set_property("cmake_file_name", "PCL")
        self.cpp_info.set_property("cmake_target_name", "PCL::PCL")
        self.cpp_info.set_property("cmake_find_mode", "both")

        for name in sorted(enabled):
            comp = self.cpp_info.components[name]
            comp.set_property("cmake_file_name", name)
            comp.set_property("cmake_module_file_name", name)
            comp.set_property("cmake_target_name", f"PCL::{name}")
            comp.set_property("pkg_config_name", f"pcl_{name}-{version_suffix}")
            comp.includedirs = [pcl_include_dir]
            if name not in PCL_HEADER_ONLY_COMPONENTS:
                comp.libs = [f"pcl_{name}"] + EXTRA_LIBS.get(name, [])
            comp.requires += INTERNAL_DEPS[name]
            for opt_dep in INTERNAL_OPTIONAL_DEPS.get(name, []):
                if self.options.get_safe(opt_dep):
                    comp.requires.append(opt_dep)
            for dep in EXTERNAL_DEPS.get(name, []) + EXTERNAL_OPTIONAL_DEPS.get(name, []):
                if dep not in used_ext or not (self.options.get_safe(f"with_{dep}") or dep in PCL_ALWAYS_ENABLED_DEPS):
                    continue
                if dep == "opengl":
                    comp.requires.append("opengl::opengl")
                    comp.requires.append("freeglut::freeglut")
                    comp.requires.append("glew::glew")
                    if is_apple_os(self) or self.settings.os == "Windows":
                        comp.requires.append("glu::glu")
                    else:
                        comp.requires.append("mesa-glu::mesa-glu")
                else:
                    comp.requires += EXTERNAL_DEP_TARGETS.get(dep, [])

        if self.options.apps:
            comp = self.cpp_info.components["apps"]
            comp.libs = []
            comp.includedirs = []
            comp.requires = list(INTERNAL_OPTIONAL_DEPS["apps"])
            for dep in EXTERNAL_OPTIONAL_DEPS["apps"]:
                if not (self.options.get_safe(f"with_{dep}") or dep in PCL_ALWAYS_ENABLED_DEPS):
                    continue
                if dep == "opengl":
                    comp.requires.append("opengl::opengl")
                    comp.requires.append("freeglut::freeglut")
                    comp.requires.append("glew::glew")
                    if is_apple_os(self) or self.settings.os == "Windows":
                        comp.requires.append("glu::glu")
                    else:
                        comp.requires.append("mesa-glu::mesa-glu")
                else:
                    comp.requires += EXTERNAL_DEP_TARGETS.get(dep, [])

        if self.options.tools:
            comp = self.cpp_info.components["tools"]
            comp.libs = []
            comp.includedirs = []
            comp.requires = list(INTERNAL_OPTIONAL_DEPS["tools"])
            for dep in EXTERNAL_OPTIONAL_DEPS["tools"]:
                if not (self.options.get_safe(f"with_{dep}") or dep in PCL_ALWAYS_ENABLED_DEPS):
                    continue
                if dep == "opengl":
                    comp.requires.append("opengl::opengl")
                    comp.requires.append("freeglut::freeglut")
                    comp.requires.append("glew::glew")
                    if is_apple_os(self) or self.settings.os == "Windows":
                        comp.requires.append("glu::glu")
                    else:
                        comp.requires.append("mesa-glu::mesa-glu")
                else:
                    comp.requires += EXTERNAL_DEP_TARGETS.get(dep, [])

        common = self.cpp_info.components["common"]
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                common.system_libs.append("pthread")
            if self.options.get_safe("with_openmp"):
                if self.settings.os == "Linux" and self.settings.compiler == "gcc":
                    common.sharedlinkflags.append("-fopenmp")
                    common.exelinkflags.append("-fopenmp")
                elif self.settings.os == "Windows":
                    if self.settings.compiler == "msvc":
                        common.system_libs.append("delayimp")
                    elif self.settings.compiler == "gcc":
                        common.system_libs.append("gomp")
        if self.settings.os == "Windows":
            common.system_libs.append("ws2_32")
        if self.options.get_safe("use_sse"):
            if not is_msvc(self):
                common.cxxflags.extend(["-msse4.2", "-mfpmath=sse"])
            else:
                common.defines.extend(
                    ["__SSE4_2__", "__SSE4_1__", "__SSSE3__", "__SSE3__", "__SSE2__", "__SSE__"]
                )
        if self.options.get_safe("use_avx"):
            common.cxxflags.append("/arch:AVX2" if is_msvc(self) else "-mavx2")
