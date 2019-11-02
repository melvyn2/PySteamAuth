#-------------------------------------------------
#
# Project created by QtCreator 2018-07-09T16:05:51
#
#-------------------------------------------------

QT       += core gui

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

QMAKE_MAC_SDK = macosx10.14

TARGET = PySteamAuth
TEMPLATE = app

FORMS += \
    MainWindow.ui \
    SetupDialog.ui \
    LogInDialog.ui \
    PhoneDialog.ui \
    CaptchaDialog.ui \
    ErrorDialog.ui \
    ConfirmationDialog.ui \
    BackupCodesDeleteDialog.ui \
    AccountChooserDialog.ui \
    BackupCodesCreatedDialog.ui

DISTFILES +=

RESOURCES += \
    Images.qrc
