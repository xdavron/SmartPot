import { Component, OnInit } from '@angular/core';


@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {

  time: any;

  constructor() { }

  ngOnInit(): void {
    setInterval(() => { this.time = new Date() }, 1000);
  }
  
}