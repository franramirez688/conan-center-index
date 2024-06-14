import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, rmdir, replace_in_file, collect_libs, save, load
from conan.tools.microsoft import is_msvc, MSBuild, MSBuildToolchain, is_msvc_static_runtime

required_conan_version = ">=1.53.0"


class SimdConan(ConanFile):
    name = "simd"
    description = "C++ image processing and machine learning library with SIMD"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/ermig1979/Simd"
    topics = ("sse", "avx", "avx-512", "amx", "vmx", "vsx", "neon")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_avx512": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_avx512": False,
    }

    @property
    def _min_cppstd(self):
        return 11

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if is_msvc(self):
            tc = MSBuildToolchain(self)
            tc.generate()
        else:
            tc = CMakeToolchain(self)
            tc.variables["SIMD_AVX512"] = self.options.with_avx512
            tc.variables["SIMD_AVX512VNNI"] = self.options.with_avx512
            tc.variables["SIMD_AVX512BF16"] = self.options.with_avx512
            tc.variables["SIMD_TEST"] = False
            tc.variables["SIMD_SHARED"] = self.options.shared
            tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
            tc.generate()

    def _patch_sources(self):
        # This is necessary to build it statically on Windows
        if not self.options.shared and is_msvc(self):
            replace_in_file(self, os.path.join(self.source_folder, "src", "Simd", "SimdConfig.h"), "//#define SIMD_STATIC", "#define SIMD_STATIC")
            replace_in_file(self, os.path.join(self.source_folder, "prj", "vs2022", "Simd.vcxproj"),
                            "<ConfigurationType>DynamicLibrary</ConfigurationType>",
                            "<ConfigurationType>StaticLibrary</ConfigurationType>")
            for prj in ("AmxBf16", "Avx2", "Avx512bw", "Avx512vnni", "Base", "Neon", "Simd", "Sse41"):
                replace_in_file(self, os.path.join(self.source_folder, "prj", "vs2022", f"{prj}.vcxproj"),
                                "    </ClCompile>",
                                "      <DebugInformationFormat>OldStyle</DebugInformationFormat>\n    </ClCompile>")
            

        if not is_msvc_static_runtime(self):
            for prj in ("AmxBf16", "Avx2", "Avx512bw", "Avx512vnni", "Base", "Neon", "Simd", "Sse41"):
                replace_in_file(self, os.path.join(self.source_folder, "prj", "vs2022", f"{prj}.vcxproj"),
                                "    </ClCompile>",
                                "      <RuntimeLibrary Condition=\"'$(Configuration)'=='Debug'\">MultiThreadedDebugDLL</RuntimeLibrary>\n      <RuntimeLibrary Condition=\"'$(Configuration)'=='Release'\">MultiThreadedDLL</RuntimeLibrary>\n    </ClCompile>")
            
            new_proj = """<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <Import Project="Prop.props" />
  <PropertyGroup Label="Globals">
    <ProjectGuid>{C809D7A3-6C52-4E36-8582-00CED929317D}</ProjectGuid>
    <Keyword>Win32Proj</Keyword>
    <ProjectName>Simd</ProjectName>
  </PropertyGroup>
  <PropertyGroup Label="Configuration">
    <ConfigurationType>StaticLibrary</ConfigurationType>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />
  <ItemDefinitionGroup>
    <ClCompile>
      <PreprocessorDefinitions>_WINDOWS;_USRDLL;%(PreprocessorDefinitions)</PreprocessorDefinitions>
      <EnableEnhancedInstructionSet Condition="'$(Platform)'=='Win32'">NoExtensions</EnableEnhancedInstructionSet>
      <EnableEnhancedInstructionSet Condition="'$(Platform)'=='x64'">NotSet</EnableEnhancedInstructionSet>
      <RuntimeLibrary Condition="'$(Configuration)'=='Debug'">MultiThreadedDebugDLL</RuntimeLibrary>
      <RuntimeLibrary Condition="'$(Configuration)'=='Release'">MultiThreadedDLL</RuntimeLibrary>
    </ClCompile>
    <Link>
      <SubSystem>Windows</SubSystem>
    </Link>
    <PreBuildEvent>
      <Command>"$(ProjectDir)..\cmd\GetVersion.cmd" "$(ProjectDir)..\.." "1"</Command>
    </PreBuildEvent>
  </ItemDefinitionGroup>
  <ItemGroup>
    <ClInclude Include="..\..\src\Simd\SimdAlignment.h" />
    <ClInclude Include="..\..\src\Simd\SimdAllocator.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdAmxBf16.h" />
    <ClInclude Include="..\..\src\Simd\SimdArray.h" />
    <ClInclude Include="..\..\src\Simd\SimdAvx2.h" />
    <ClInclude Include="..\..\src\Simd\SimdAvx512bw.h" />
    <ClInclude Include="..\..\src\Simd\SimdAvx512vnni.h" />
    <ClInclude Include="..\..\src\Simd\SimdBase.h" />
    <ClInclude Include="..\..\src\Simd\SimdConfig.h" />
    <ClInclude Include="..\..\src\Simd\SimdConst.h" />
    <ClInclude Include="..\..\src\Simd\SimdContour.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdCopy.h" />
    <ClInclude Include="..\..\src\Simd\SimdCpu.h" />
    <ClInclude Include="..\..\src\Simd\SimdDefs.h" />
    <ClInclude Include="..\..\src\Simd\SimdDescrInt.h" />
    <ClInclude Include="..\..\src\Simd\SimdDetection.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdDrawing.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdEmpty.h" />
    <ClInclude Include="..\..\src\Simd\SimdEnable.h" />
    <ClInclude Include="..\..\src\Simd\SimdErf.h" />
    <ClInclude Include="..\..\src\Simd\SimdExp.h" />
    <ClInclude Include="..\..\src\Simd\SimdExtract.h" />
    <ClInclude Include="..\..\src\Simd\SimdFmadd.h" />
    <ClInclude Include="..\..\src\Simd\SimdFont.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdFrame.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdGaussianBlur.h" />
    <ClInclude Include="..\..\src\Simd\SimdGemm.h" />
    <ClInclude Include="..\..\src\Simd\SimdImageLoad.h" />
    <ClInclude Include="..\..\src\Simd\SimdImageMatcher.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdImageSave.h" />
    <ClInclude Include="..\..\src\Simd\SimdInit.h" />
    <ClInclude Include="..\..\src\Simd\SimdLib.h" />
    <ClCompile Include="..\..\src\Simd\SimdLib.cpp" />
    <ClInclude Include="..\..\src\Simd\SimdLib.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdLoad.h" />
    <ClInclude Include="..\..\src\Simd\SimdLog.h" />
    <ClInclude Include="..\..\src\Simd\SimdMath.h" />
    <ClInclude Include="..\..\src\Simd\SimdMemory.h" />
    <ClInclude Include="..\..\src\Simd\SimdMemoryStream.h" />
    <ClInclude Include="..\..\src\Simd\SimdMotion.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdMsa.h" />
    <ClInclude Include="..\..\src\Simd\SimdNeon.h" />
    <ClInclude Include="..\..\src\Simd\SimdNeural.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdParallel.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdPerformance.h" />
    <ClInclude Include="..\..\src\Simd\SimdPixel.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdPoint.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdPoly.h" />
    <ClInclude Include="..\..\src\Simd\SimdPyramid.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdRectangle.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdRecursiveBilateralFilter.h" />
    <ClInclude Include="..\..\src\Simd\SimdResizer.h" />
    <ClInclude Include="..\..\src\Simd\SimdRuntime.h" />
    <ClInclude Include="..\..\src\Simd\SimdShift.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdSse41.h" />
    <ClInclude Include="..\..\src\Simd\SimdStore.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynet.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetConvolution16b.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetConvolution32f.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetConvolution32fCommon.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetConvolution8i.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetConvolution8iCommon.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetConvParam.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetDeconvolution32f.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetGridSample.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetInnerProduct32f.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetMergedConvolution32f.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetMergedConvolution32fBf16.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetMergedConvolution8i.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetPermute.h" />
    <ClInclude Include="..\..\src\Simd\SimdSynetScale8i.h" />
    <ClInclude Include="..\..\src\Simd\SimdTime.h" />
    <ClInclude Include="..\..\src\Simd\SimdUnpack.h" />
    <ClInclude Include="..\..\src\Simd\SimdVersion.h" />
    <ClInclude Include="..\..\src\Simd\SimdView.hpp" />
    <ClInclude Include="..\..\src\Simd\SimdWarpAffine.h" />
    <ClInclude Include="..\..\src\Simd\SimdXml.hpp" />
  </ItemGroup>
  <ItemGroup>
    
  </ItemGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.targets" />
</Project>
"""
            save(self, os.path.join(self.source_folder, "prj", "vs2022", "Simd.vcxproj"), new_proj)
            replace_in_file(self, os.path.join(self.source_folder, "src", "Simd", "SimdLib.cpp"), "SIMD_API const char * SimdVersion()", "const char * SimdVersion()")
            content = load(self, os.path.join(self.source_folder, "src", "Simd", "SimdLib.h"), encoding="latin")#, )
            content = content.replace("SIMD_API const char * SimdVersion()", "const char * SimdVersion()")
            save(self, os.path.join(self.source_folder, "src", "Simd", "SimdLib.h"), content)

    def build(self):
        self._patch_sources()
        if is_msvc(self):
            msbuild = MSBuild(self)
            msbuild.build(os.path.join(self.source_folder, "prj", "vs2022", "Simd.vcxproj"))
        else:
            cmake = CMake(self)
            cmake.configure(build_script_folder=os.path.join(self.source_folder, "prj", "cmake"))
            cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        if is_msvc(self):
            copy(self, pattern="*.h*", dst=os.path.join(self.package_folder, "include", "Simd"), src=os.path.join(self.source_folder, "src", "Simd"), keep_path=True)
            copy(self, pattern="*.lib", dst=os.path.join(self.package_folder, "lib"), src=self.source_folder, keep_path=False)
            copy(self, pattern="*.dll", dst=os.path.join(self.package_folder, "bin"), src=self.source_folder, keep_path=False)
        else:
            cmake = CMake(self)
            cmake.install()
            rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "Simd")
        self.cpp_info.set_property("cmake_target_name", "Simd::Simd")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("pthread")
            self.cpp_info.system_libs.append("m")
