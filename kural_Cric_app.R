library(dplyr)
library(DT)
library(writexl)
library(shiny)
library(shinythemes)
library(shinyauthr)

############################################################################
# Define user credentials
############################################################################
credentials <- data.frame(
  user = c("Admin", "Player"),          # Usernames
  password = c("Cric@1234", "Play@1234"), # Passwords
  role = c("editor", "viewer"),         # Roles
  stringsAsFactors = FALSE
)

############################################################################
# Create an empty data frame for a new month
############################################################################
createEmptyMonthData <- function(players) {
  data.frame(
    Name         = players,
    PrevBalance  = 0,
    MonthAdvance = 0,
    TotalAdvance = 0,
    Balance      = 0,
    stringsAsFactors = FALSE
  )
}

############################################################################
# Recalculate each row's Balance
############################################################################
recalcBalance <- function(df) {
  game_cols <- grep("\\(€", names(df), value = TRUE)
  
  for (i in seq_len(nrow(df))) {
    adv <- df$PrevBalance[i] + df$MonthAdvance[i]
    df$TotalAdvance[i] <- adv
    
    if (adv == 0) {
      df$Balance[i] <- 0
    } else {
      totalCost <- 0
      for (gc in game_cols) {
        if (!is.na(df[i, gc]) && df[i, gc] == "P") {
          cost_str <- sub(".*\\(€(.*)\\).*", "\\1", gc)
          cost_num <- as.numeric(cost_str)
          if (!is.na(cost_num)) {
            totalCost <- totalCost + cost_num
          }
        }
      }
      df$Balance[i] <- adv - totalCost
      if (df$Balance[i] < 0) df$Balance[i] <- 0
    }
  }
  
  df %>%
    select(
      Name,
      PrevBalance,
      MonthAdvance,
      TotalAdvance,
      all_of(grep("\\(€", names(df), value = TRUE)),
      Balance,
      everything()
    )
}

############################################################################
# Save and load data functions
############################################################################
saveData <- function(data) {
  saveRDS(data, file = "game_data.rds")
}

loadData <- function() {
  if (file.exists("game_data.rds")) {
    readRDS("game_data.rds")
  } else {
    NULL
  }
}

############################################################################
# UI
############################################################################
ui <- fluidPage(
  theme = shinytheme("cerulean"),
  
  # CSS for logout alignment and disabled buttons
  tags$head(tags$style(HTML("
    .logout-btn { float: right; }
    .disabled-button { pointer-events: none; opacity: 0.5; }
  "))),
  
  # Logout button
  div(class = "logout-btn", 
      shinyauthr::logoutUI(id = "logout", label = "Logout", class = "btn btn-danger")),
  
  # Title
  titlePanel("Monthly Cricket Attendance and Balance"),
  
  # Login module
  shinyauthr::loginUI(id = "login"),
  
  # Main content after authentication
  uiOutput("auth_content")
)

############################################################################
# SERVER
############################################################################
server <- function(input, output, session) {
  
  # --- AUTHENTICATION ---
  credentials_reactive <- shinyauthr::loginServer(
    id = "login",
    data = credentials,
    user_col = user,
    pwd_col = password,
    log_out = reactive(logout_init())
  )
  
  logout_init <- shinyauthr::logoutServer(
    id = "logout",
    reactive(credentials_reactive()$user_auth)
  )
  
  # --- INITIAL DATA ---
  initial_data <- loadData()
  basePlayers <- c(
    "Akhil", "Akshy", "Anil", "Arun GB", "Arun S", "Ashok", "Banu", "Palani",
    "Dinesh", "Gobi", "Harshit", "Jeevan", "Joseph", "Kousal", "Krishna", "Kural",
    "Mani", "Naranyan reddy", "Nisanth", "Nirmal", "Poorna", "Prem", "Ramu", "Rishi",
    "Sam", "Siva", "Surya", "Sankreeth", "Vinith Pradeep", "Pankaj", "Harindra", "Vaishak"
  )
  values <- reactiveValues(
    data = if (!is.null(initial_data)) initial_data else list(
      "January" = createEmptyMonthData(basePlayers)
    )
  )
  
  # --- DYNAMIC UI AFTER LOGIN ---
  output$auth_content <- renderUI({
    req(credentials_reactive()$user_auth)
    role <- credentials_reactive()$info$role
    button_class <- if (role == "viewer") "disabled-button" else ""
    
    sidebarLayout(
      sidebarPanel(
        width = 3, 
        actionButton("save_changes", "Save Changes", class = button_class),
        hr(),
        h4("Manage Months"),
        selectInput("selectedMonth", "Select Month:", choices = names(values$data),
                    selected = names(values$data)[1]),
        textInput("newMonthName", "New Month Name:", ""),
        actionButton("createNewMonth", "Add New Month", class = button_class),
        selectInput("deleteMonth", "Delete Month:", choices = names(values$data)),
        actionButton("deleteMonthBtn", "Confirm Delete Month", class = button_class),
        hr(),
        h4("Add Player"),
        textInput("newPlayerName", "Player Name:", ""),
        actionButton("addPlayer", "Add Player", class = button_class),
        selectInput("deletePlayer", "Delete Player:", choices = NULL),
        actionButton("deletePlayerBtn", "Confirm Delete Player", class = button_class),
        hr(),
        h4("Add Game"),
        dateInput("game_date", "Game Date:", value = Sys.Date()),
        numericInput("game_cost", "Cost per Player (EUR):", 4.5, min = 0, step = 0.01),
        actionButton("add_game", "Add Game", class = button_class),
        hr(),
        h4("Delete Game"),
        selectInput("delete_game", "Select Game Column to Delete:", choices = ""),
        actionButton("delete_game_btn", "Delete Selected Game"),
        hr(),
        # --- Common Player Selection (only once)
        h4("Select Players"),
        checkboxGroupInput("selected_players", "Select Players:", choices = basePlayers),
        hr(),
        # --- Update Attendance Section (using common player selection)
        h4("Update Attendance"),
        selectInput("selected_game", "Select Game Column:", choices = NULL),
        radioButtons("mode", "Update Mode", 
                     choices = c("Only update selected", "Selected P, Rest E"),
                     selected = "Only update selected"),
        selectInput("attendance", "Select Attendance:", choices = c("P", "E", "Y")),
        actionButton("set_attendance", "Set Attendance", class = button_class),
        hr(),
        # --- Set Monthly Advance Section (using common player selection)
        h4("Set Monthly Advance"),
        numericInput("advance_payment", "Monthly Advance (EUR):", value = 22, min = 0),
        actionButton("set_advance", "Set Advance", class = button_class),
        hr(),
        downloadButton("download_data", "Download Excel")
      ),
      mainPanel(
        uiOutput("monthHeaderUI"),
        DTOutput("month_table")
      )
    )
  })
  
  # --- RENDER DT TABLE (with Total and Total Played rows; values rounded) ---
  output$month_table <- renderDT({
    req(credentials_reactive()$user_auth)
    req(input$selectedMonth)
    
    mon <- input$selectedMonth
    df_orig <- values$data[[mon]]
    if (is.null(df_orig) || nrow(df_orig) == 0) {
      return(datatable(data.frame()))
    }
    df <- df_orig
    game_cols <- grep("\\(€", names(df), value = TRUE)
    
    # Compute Total Row (rounded to 2 decimals)
    total_row <- setNames(rep("", ncol(df)), names(df))
    total_row["Name"] <- "Total"
    numeric_cols <- c("PrevBalance", "MonthAdvance", "TotalAdvance", "Balance")
    for (col in numeric_cols) {
      if (col %in% names(df)) {
        total_row[col] <- round(sum(as.numeric(df[[col]]), na.rm = TRUE), 2)
      }
    }
    for (game in game_cols) {
      total_row[game] <- round(sum(
        ifelse(df[[game]] == "P", 
               as.numeric(sub(".*\\(€(.*)\\).*", "\\1", game)), 0),
        na.rm = TRUE), 2)
    }
    
    # Compute Total Played Row (count players with "P" or "Y")
    total_played <- setNames(rep("", ncol(df)), names(df))
    total_played["Name"] <- "Total Played"
    for (game in game_cols) {
      total_played[game] <- sum(df[[game]] %in% c("P", "Y"), na.rm = TRUE)
    }
    
    df_display <- rbind(df, total_row, total_played)
    
    datatable(
      df_display,
      editable = if (credentials_reactive()$info$role == "editor") list(target = "cell") else FALSE,
      options = list(pageLength = 50, lengthMenu = c(10, 25, 50, 100), scrollX = TRUE)
    )
  }, server = FALSE)
  
  # --- OBSERVE CELL EDITS (only editors can edit) ---
  observeEvent(input$month_table_cell_edit, {
    req(credentials_reactive()$info$role == "editor")
    info <- input$month_table_cell_edit
    mon <- input$selectedMonth
    df <- values$data[[mon]]
    if (is.null(df)) return()
    row <- info$row; col <- info$col; value <- info$value
    df[row, col] <- value
    df <- recalcBalance(df)
    values$data[[mon]] <- df
  })
  
  # --- UPDATE SELECTINPUTS ---
  observe({
    months <- names(values$data)
    updateSelectInput(session, "selectedMonth", choices = months, selected = input$selectedMonth)
    updateSelectInput(session, "deleteMonth", choices = months)
  })
  
  observe({
    mon <- input$selectedMonth
    if (!is.null(mon) && mon %in% names(values$data)) {
      players <- values$data[[mon]]$Name
      updateSelectInput(session, "deletePlayer", choices = players)
    }
  })
  
  observe({
    mon <- input$selectedMonth
    if (!is.null(mon) && mon %in% names(values$data)) {
      games <- names(values$data[[mon]])[5:ncol(values$data[[mon]])]
      updateSelectInput(session, "delete_game", choices = games)
    }
  })
  
  # --- PRESERVE THE SELECTED GAME COLUMN WHEN UPDATING THE CHOICES ---
  observe({
    mon <- input$selectedMonth
    if (!is.null(mon) && mon %in% names(values$data)) {
      game_cols <- grep("\\(€", names(values$data[[mon]]), value = TRUE)
      # Preserve the current selection if possible, else choose the last game (most recent)
      current <- isolate(input$selected_game)
      if (length(current) == 0 || !(current %in% game_cols)) {
        current <- if (length(game_cols) > 0) game_cols[length(game_cols)] else ""
      }
      updateSelectInput(session, "selected_game", choices = game_cols, selected = current)
    }
  })
  
  # --- CREATE NEW MONTH ---
  observeEvent(input$createNewMonth, {
    req(credentials_reactive()$info$role == "editor")
    newName <- trimws(input$newMonthName)
    if (!nzchar(newName)) {
      showNotification("Enter a new month name.", type = "error")
      return()
    }
    if (newName %in% names(values$data)) {
      showNotification("That month already exists!", type = "error")
      return()
    }
    oldMonth <- input$selectedMonth
    oldDF <- recalcBalance(values$data[[oldMonth]])
    newDF <- data.frame(
      Name = oldDF$Name,
      PrevBalance = oldDF$Balance,
      MonthAdvance = 0,
      TotalAdvance = 0,
      Balance = 0,
      stringsAsFactors = FALSE
    )
    newDF <- recalcBalance(newDF)
    values$data[[newName]] <- newDF
    updateTextInput(session, "newMonthName", value = "")
    updateSelectInput(session, "selectedMonth", selected = newName)
  })
  
  # --- DELETE MONTH ---
  observeEvent(input$deleteMonthBtn, {
    req(credentials_reactive()$info$role == "editor")
    delMonth <- input$deleteMonth
    if (nzchar(delMonth)) {
      values$data[[delMonth]] <- NULL
      if (length(values$data) > 0) {
        updateSelectInput(session, "selectedMonth", selected = names(values$data)[1])
      } else {
        updateSelectInput(session, "selectedMonth", choices = character(0))
      }
    }
  })
  
  # --- ADD PLAYER ---
  observeEvent(input$addPlayer, {
    req(credentials_reactive()$info$role == "editor")
    mon <- input$selectedMonth
    df <- values$data[[mon]]
    pName <- trimws(input$newPlayerName)
    if (!nzchar(pName)) {
      showNotification("Please enter a valid player name.", type = "error")
      return()
    }
    if (pName %in% df$Name) {
      showNotification("Player already exists.", type = "error")
      return()
    }
    new_row <- as.data.frame(matrix("", nrow = 1, ncol = ncol(df)))
    names(new_row) <- names(df)
    new_row$Name <- pName
    new_row$PrevBalance <- 0
    new_row$MonthAdvance <- 0
    new_row$TotalAdvance <- 0
    new_row$Balance <- 0
    is_total_row <- df$Name == "Total"
    if (any(is_total_row)) {
      df <- rbind(df[!is_total_row, ], new_row, df[is_total_row, ])
    } else {
      df <- rbind(df, new_row)
    }
    df <- recalcBalance(df)
    values$data[[mon]] <- df
    updateTextInput(session, "newPlayerName", value = "")
    updateSelectInput(session, "deletePlayer", choices = df$Name)
  })
  
  # --- DELETE PLAYER ---
  observeEvent(input$deletePlayerBtn, {
    req(credentials_reactive()$info$role == "editor")
    mon <- input$selectedMonth
    df <- values$data[[mon]]
    delName <- input$deletePlayer
    if (delName %in% df$Name) {
      df <- df[df$Name != delName, ]
      df <- recalcBalance(df)
      values$data[[mon]] <- df
    }
  })
  
  # --- ADD GAME ---
  observeEvent(input$add_game, {
    req(credentials_reactive()$info$role == "editor")
    mon <- input$selectedMonth
    df <- values$data[[mon]]
    colName <- paste0(format(input$game_date, "%d/%m/%Y"), " (€", input$game_cost, ")")
    if (!colName %in% names(df)) {
      df[[colName]] <- NA_character_
      df <- recalcBalance(df)
      values$data[[mon]] <- df
    }
  })
  
  # --- DELETE GAME ---
  observeEvent(input$delete_game_btn, {
    req(credentials_reactive()$info$role == "editor")
    mon <- input$selectedMonth
    df <- values$data[[mon]]
    game_col <- input$delete_game
    if (game_col %in% names(df)) {
      df <- df %>% select(-all_of(game_col))
      df <- recalcBalance(df)
      values$data[[mon]] <- df
    }
  })
  
  # --- SET MONTH ADVANCE ---
  observeEvent(input$set_advance, {
    req(credentials_reactive()$info$role == "editor")
    mon <- input$selectedMonth
    df <- values$data[[mon]]
    selected_players <- input$selected_players
    df$MonthAdvance <- ifelse(df$Name %in% selected_players, 
                              df$MonthAdvance + input$advance_payment,
                              df$MonthAdvance)
    df <- recalcBalance(df)
    values$data[[mon]] <- df
  })
  
  # --- UPDATE ATTENDANCE (using common player selection) ---
  observeEvent(input$set_attendance, {
    req(credentials_reactive()$info$role == "editor")
    mon <- input$selectedMonth
    df <- values$data[[mon]]
    selected_game <- input$selected_game
    if (!selected_game %in% names(df)) {
      showNotification("Selected game column not found!", type = "error")
      return()
    }
    if (input$mode == "Only update selected") {
      selected_players <- input$selected_players
      if (length(selected_players) == 0) {
        showNotification("Please select at least one player.", type = "error")
        return()
      }
      df[df$Name %in% selected_players, selected_game] <- input$attendance
    } else if (input$mode == "Selected P, Rest E") {
      df[[selected_game]] <- ifelse(df$Name %in% input$selected_players, "P", "E")
    }
    df <- recalcBalance(df)
    values$data[[mon]] <- df
  })
  
  # --- SAVE CHANGES ---
  observeEvent(input$save_changes, {
    req(credentials_reactive()$info$role == "editor")
    saveData(values$data)
    showNotification("Changes saved!", type = "message")
  })
  
  # --- MONTH HEADER UI ---
  output$monthHeaderUI <- renderUI({
    mon <- input$selectedMonth
    if (!mon %in% names(values$data)) {
      HTML("<h3>No data for that month.</h3>")
    } else {
      HTML(paste0(
        "<h3>Attendance & Balances for ", mon, "</h3>",
        "<p style='color:blue;'><strong>P = Present, E = Excused Absence, Y = Yet to Pay</strong></p>"
      ))
    }
  })
  
  # --- DOWNLOAD HANDLER (with Total and Total Played rows; values rounded to 2 decimals) ---
  output$download_data <- downloadHandler(
    filename = function() {
      paste0("game_data_", input$selectedMonth, "_", Sys.Date(), ".xlsx")
    },
    content = function(file) {
      selectedMonth <- input$selectedMonth
      if (!is.null(selectedMonth) && selectedMonth %in% names(values$data)) {
        month_data <- values$data[[selectedMonth]]
        
        # Compute Total Row (rounded to 2 decimals)
        game_cols <- grep("\\(€", names(month_data), value = TRUE)
        total_row <- setNames(rep("", ncol(month_data)), names(month_data))
        total_row["Name"] <- "Total"
        numeric_cols <- c("PrevBalance", "MonthAdvance", "TotalAdvance", "Balance")
        for (col in numeric_cols) {
          if (col %in% names(month_data)) {
            total_row[col] <- round(sum(as.numeric(month_data[[col]]), na.rm = TRUE), 2)
          }
        }
        for (game in game_cols) {
          total_row[game] <- round(sum(
            ifelse(month_data[[game]] == "P",
                   as.numeric(sub(".*\\(€(.*)\\).*", "\\1", game)), 0),
            na.rm = TRUE), 2)
        }
        
        # Compute Total Played Row (count of players with "P" or "Y")
        total_played <- setNames(rep("", ncol(month_data)), names(month_data))
        total_played["Name"] <- "Total Played"
        for (game in game_cols) {
          total_played[game] <- sum(month_data[[game]] %in% c("P", "Y"), na.rm = TRUE)
        }
        
        df_out <- rbind(month_data, total_row, total_played)
        writexl::write_xlsx(df_out, path = file)
      } else {
        writexl::write_xlsx(data.frame(), path = file)
      }
    }
  )
}

shinyApp(ui = ui, server = server)
