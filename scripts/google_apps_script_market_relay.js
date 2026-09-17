/**
 * Pozitron Market - Autonomous Cloud Order Relay & Google Sheets Webhook
 * 
 * Instructions for User:
 * 1. Open your Google Apps Script editor associated with your Google Sheet:
 *    (https://script.google.com/macros/s/AKfycbw_YHCFvOkkq2usjJh4XCMMHWgHy9V_7C5fROFCjrTGw1iGsPy_39o6JXyvlowO9iy5/edit)
 * 2. Replace the script code with this file.
 * 3. In Google Apps Script: Project Settings -> Script Properties -> Add property:
 *    Key: GITHUB_PAT
 *    Value: <Your GitHub Personal Access Token with repo / contents:write scope>
 *    (If GITHUB_PAT is not set, orders are still safely logged to Google Sheets as usual).
 * 4. Deploy as Web App (Execute as: Me, Who has access: Anyone).
 * 
 * STRICT ZERO EMOJIS.
 */

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "Empty payload" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    // 1. User Registration Handler
    if (data.type === 'user') {
      var userSheet = ss.getSheetByName("Kullanıcılar") || ss.insertSheet("Kullanıcılar");
      if (userSheet.getLastRow() === 0) {
        userSheet.appendRow(["Ad Soyad", "E-posta", "Sağlayıcı", "Rol", "Kayıt Tarihi"]);
      }
      userSheet.appendRow([
        data.full_name || "",
        data.email || "",
        data.provider || "manual",
        data.role || "customer",
        data.registered_at || new Date().toISOString()
      ]);
      return ContentService.createTextOutput(JSON.stringify({ status: "success", type: "user_recorded" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // 2. Stock Alert Notification Handler
    if (data.type === 'stock_alert') {
      var alertSheet = ss.getSheetByName("Stok Bildirimleri") || ss.insertSheet("Stok Bildirimleri");
      if (alertSheet.getLastRow() === 0) {
        alertSheet.appendRow(["Ürün ID", "Ürün Adı", "E-posta", "Telefon", "Tarih"]);
      }
      alertSheet.appendRow([
        data.prod_id || "",
        data.prod_name || "",
        data.email || "",
        data.phone || "",
        data.created_at || new Date().toISOString()
      ]);
      return ContentService.createTextOutput(JSON.stringify({ status: "success", type: "stock_alert_recorded" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // 3. Purchase Order Handler
    var orderSheet = ss.getSheetByName("Siparişler") || ss.insertSheet("Siparişler");
    if (orderSheet.getLastRow() === 0) {
      orderSheet.appendRow([
        "Sipariş No", "Tarih", "Müşteri Adı", "E-posta", "Telefon",
        "Adres", "Ürünler", "Tutar (TL)", "Tutar (USD)", "Ödeme Yöntemi", "İşlem No"
      ]);
    }

    var orderNumber = data.order_number || ("PZT-" + Utilities.formatDate(new Date(), "GMT+3", "yyyyMMdd-HHmmss"));
    var itemsSummary = "";
    if (Array.isArray(data.items_detail)) {
      itemsSummary = data.items_detail.map(function(i) {
        return (i.quantity || 1) + "x " + (i.name || i.sku || "Ürün");
      }).join(", ");
    } else if (typeof data.items === 'string') {
      itemsSummary = data.items;
    }

    orderSheet.appendRow([
      orderNumber,
      data.created_at || new Date().toISOString(),
      data.name || data.customer_name || "Misafir",
      data.email || data.customer_email || "",
      data.phone || data.customer_phone || "",
      data.shipping_address || "",
      itemsSummary,
      data.total_try || "0.00",
      data.total_usd || "0.00",
      data.card_brand || data.payment_method || "Kredi Kartı",
      data.transaction_id || ""
    ]);

    // 4. Cloud Repository Dispatch Relay to GitHub Actions
    var dispatched = false;
    var githubToken = PropertiesService.getScriptProperties().getProperty("GITHUB_PAT");
    if (githubToken) {
      try {
        var repoOwner = "thepeakiscold";
        var repoName = "pozitron-market";
        var dispatchUrl = "https://api.github.com/repos/" + repoOwner + "/" + repoName + "/dispatches";

        var payload = {
          event_type: "order_placed",
          client_payload: {
            order: data
          }
        };

        var options = {
          method: "post",
          headers: {
            "Authorization": "Bearer " + githubToken,
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Pozitron-GAS-Relay"
          },
          contentType: "application/json",
          payload: JSON.stringify(payload),
          muteHttpExceptions: true
        };

        var res = UrlFetchApp.fetch(dispatchUrl, options);
        if (res.getResponseCode() === 204) {
          dispatched = true;
        }
      } catch (ghErr) {
        // Log quietly in Apps Script execution log
        console.error("GitHub dispatch notice: " + ghErr);
      }
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      order_number: orderNumber,
      sheet_recorded: true,
      cloud_stock_dispatched: dispatched
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "online",
    service: "Pozitron Market Autonomous Cloud Order Relay",
    timestamp: new Date().toISOString()
  })).setMimeType(ContentService.MimeType.JSON);
}
