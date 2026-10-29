#include <cstdlib>
#include <iostream>
#include <QCoreApplication>
#include <limereport/LimeReport>
#include <limereport/version.h>

int main(int argc, char* argv[])
{
    // ReportEngine creates a QPrinter, which requires an application instance
    QCoreApplication app(argc, argv);
    auto report = new LimeReport::ReportEngine();

    std::cout << "limereport: " << report->reportName().toStdString() << std::endl;
    std::cout << "LIMEREPORT_VERSION_STR: " << LIMEREPORT_VERSION_STR << std::endl;

    delete report;
    return EXIT_SUCCESS;
}
