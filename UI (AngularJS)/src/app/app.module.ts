import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { MDBBootstrapModule } from 'angular-bootstrap-md';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { MainComponent } from './main/main.component';
import { RoseComponent } from './rose/rose.component';
import { ManualComponent } from './rose/manual/manual.component';
import { AutomaticComponent } from './rose/automatic/automatic.component';
import { DashboardComponent } from './rose/dashboard/dashboard.component';
import { FeedbackComponent } from './rose/feedback/feedback.component';

@NgModule({
  declarations: [
    AppComponent,
    MainComponent,
    RoseComponent,
    ManualComponent,
    AutomaticComponent,
    DashboardComponent,
    FeedbackComponent
  ],
  imports: [
    BrowserModule,
    MDBBootstrapModule.forRoot(),
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    AppRoutingModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
