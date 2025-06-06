<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c"%>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean"%>
<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html"%>
<%@ taglib uri="http://www.opensymphony.com/sitemesh/decorator" prefix="decorator"%>
<%@ taglib uri="http://www.opensymphony.com/sitemesh/page" prefix="page"%>
<%@ taglib uri="http://rhn.redhat.com/rhn" prefix="rhn"%>
<%@ page import="com.redhat.rhn.common.conf.Config"%>
<%@ page import="com.redhat.rhn.common.conf.ConfigDefaults"%>
<%@ page import="com.redhat.rhn.GlobalInstanceHolder" %>
<%@ page contentType="text/html; charset=UTF-8"
%><!DOCTYPE HTML>
<html:html lang="true">
  <head>
    <!-- enclosing head tags in layout_c.jsp -->
    <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
<%--    <c:if test="${pageContext.request.requestURI == '/rhn/Load.do'}">--%>
<%--      <meta http-equiv="refresh" content="0; url=<c:out value="${param.return_url}" />" />--%>
<%--    </c:if>--%>
    <meta http-equiv="content-type" content="text/html;charset=UTF-8"/>
    <title>
      <bean:message key="layout.jsp.productname"/>
    </title>
    <link rel="shortcut icon" href="/img/favicon.ico" />

    <meta name="viewport" content="width=device-width, initial-scale=1.0" />

    <c:set var="cb_version" value="${rhn:getConfig('web.buildtimestamp')}" />

    <!-- import default fonts/icons styles -->
    <link rel="stylesheet" href="/fonts/font-awesome/css/font-awesome.css?cb=${cb_version}" />
    <!-- import custom fonts/icons styles -->
    <link rel="stylesheet" href="/fonts/font-spacewalk/css/spacewalk-font.css?cb=${cb_version}" />

    <c:set var="webTheme" value="${ConfigDefaults.get().getDefaultWebTheme()}"/>
    <!-- import styles -->
    <link rel="stylesheet" href="/css/updated-${webTheme}.css?cb=${cb_version}" />

    <!-- expose user preferred language to the application -->
    <c:set var="currentLocale" value="${ConfigDefaults.get().getDefaultLocale()}"/>
    <script>window.preferredLocale='${currentLocale}'</script>

    <!-- expose user preferred documentation language to the application -->
    <c:set var="docsLocale" value="${ConfigDefaults.get().getDefaultDocsLocale()}"/>
    <script>window.docsLocale='${docsLocale}'</script>

    <script src="/javascript/jquery.js?cb=${cb_version}"></script>
    <script src="/javascript/bootstrap.js?cb=${cb_version}"></script>
    <script src="/javascript/spacewalk-essentials.js?cb=${cb_version}"></script>
    <script src="/javascript/spacewalk-checkall.js?cb=${cb_version}"></script>

    <script src='/javascript/manager/main.js?cb=${cb_version}'></script>
    <script src='/javascript/momentjs/moment-with-langs.min.js?cb=${cb_version}' type='text/javascript'></script>
    <decorator:head />
  </head>
  <c:set var="webTheme" value="${GlobalInstanceHolder.USER_PREFERENCE_UTILS.getCurrentWebTheme(pageContext)}"/>
  <body class="theme-${webTheme} new-theme" onload="<decorator:getProperty property="body.onload" />">
    <c:set var="custom_header" scope="page" value="${rhn:getConfig('java.custom_header')}" />

    <header class="navbar-pf navbar">
      <div class="header-content container-fluid">
        <div class="navbar-header d-flex flex-row">
          <a class="navbar-toggle" data-bs-toggle="collapse" href="#spacewalk-aside">
            <i class="fa fa-bars" aria-hidden="true"></i>
          </a>
          <div id="breadcrumb">
            <div>
              <c:choose>
                <c:when test="${Config.get().getString('product_name').compareToIgnoreCase('Uyuni') == 0 }">
                  <a href="/" class="navbar-brand js-spa" target="" title="Uyuni homepage">
                    <span>Uyuni</span>
                  </a>
                </c:when>
                <c:otherwise>
                  <a href="/" class="navbar-brand js-spa" target="" title="SUSE Multi-Linux Manager homepage">
                    <span>SUSE<i class="fa fa-registered"></i> Multi-Linux Manager</span>
                  </a>
                </c:otherwise>
              </c:choose>
            </div>
          </div>
        </div>
    </header>

    <div class="spacewalk-main-column-layout">
      <aside id="spacewalk-aside" class="navbar-collapse collapse collapse-horizontal show">
        <div id="nav">
          <nav class="collapsed">
            <ul class="level1">
              <li>
                <div class="nodeLink">
                  <i class="fa fa-home"></i><a href="/" class="js-spa">Home</a>
                </div>
              </li>
              <li>
                <div class="nodeLink">
                  <c:choose>
                    <c:when test="${Config.get().getString('product_name').compareToIgnoreCase('Uyuni') == 0 }">
                      <i class="fa fa-link"></i><a href="https://www.uyuni-project.org/uyuni-docs/uyuni/index.html" class="js-spa" target="_blank"><bean:message key="header.jsp.documentation"/></a>
                    </c:when>
                    <c:otherwise>
                      <i class="fa fa-link"></i><a href="https://documentation.suse.com/suma/" class="js-spa" target="_blank"><bean:message key="header.jsp.documentation"/></a>
                    </c:otherwise>
                  </c:choose>
                </div>
              </li>
            </ul>
          </nav>
        </div>

        <footer>
          <div class="wrapper">
            <div class="footer-release">
              <bean:message key="footer.jsp.release" arg0="/docs/${docsLocale}/release-notes/release-notes-server.html" arg1="${rhn:getProductVersion()}" />
            </div>
            <c:set var="custom_footer" scope="page" value="${rhn:getConfig('java.custom_footer')}" />
            <c:if test="${! empty custom_footer}">
              <div><c:out value="${custom_footer}" escapeXml="false"/></div>
            </c:if>
          </div>
        </footer>
      </aside>

      <div id="page-body">
        <div id="page-body-default">
          <section id="spacewalk-content">
            <decorator:body />
          </section>
        </div>
        <script type="text/javascript">
          <c:if test="${rhn:getConfig('web.spa.enable')}">
            <c:set var="spaTimeout" value="${rhn:getConfig('web.spa.timeout')}"/>
            window.pageRenderers && window.pageRenderers.spaengine.init && window.pageRenderers.spaengine.init(${spaTimeout});
          </c:if>
        </script>
      </div>
    </div>
  </body>
</html:html>
